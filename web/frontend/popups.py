"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import logging
import shutil
import re

from schema.schema import getMetadataType
from lib.pdf import printview

from schema.schema import VIEW_DATA_ONLY, VIEW_HIDE_EMPTY
from core.translation import t, lang
from utils.utils import getCollection
from core import webconfig
from core import db
from core import Node
from contenttypes import Container
from utils.pathutils import getPaths
from utils import userinput
from core import httpstatus
from core.request_handler import sendFile as _sendFile

#
# execute fullsize method from node-type
#


logg = logging.getLogger(__name__)
q = db.query


def popup_fullsize(req):
    nid = userinput.string_to_int(req.args.get("id", type=int))
    if nid is None:
        return 400
    
    node = q(Node).get(nid)
    if not isinstance(node, Node):
        return 404
    
    version_id = req.params.get("v")
    version = node.get_tagged_version(unicode(version_id))

    node_or_version = version if version else node
    return node_or_version.popup_fullsize(req)
#
# execute thumbBig method from node-type
#


def popup_thumbbig(req):
    node = q(Node).get(req.params["id"])
    if not isinstance(node, Node):
        return 404
    return node.popup_thumbbig(req)


#
# help window for metadata field
#
def show_help(req):
    if req.params.get("maskid", "") != "":
        field = q(Node).get(req.params.get("maskid", ""))
    else:
        field = q(Node).get(req.params.get("id", ""))
    html = webconfig.theme.render_macro("popups.j2.jade", "show_help", {"field": field})
    req.write(html)

#
# show attachmentbrowser for given node
# parameter: req.id, req.path
#


def show_attachmentbrowser(req):
    nid = req.params.get("id")
    node = q(Node).get(nid)
    if not node.has_data_access():
        req.write(t(req, "permission_denied"))
        return

    from core.attachment import getAttachmentBrowser
    getAttachmentBrowser(node, req)


def getPrintChildren(req, node, ret):
    for c in node.children.filter_read_access().prefetch_attrs():
        ret.append(c)
        if c.isContainer():
            getPrintChildren(req, c, ret)
        else:
            # this is a content node which has only in rare cases children
            # use nodemapping to detect children before calling getPrintChildren
            children_ids = db.session.execute("select cid from nodemapping where nid = %d" % c.id)
            cids = [row['cid'] for row in children_ids]
            del children_ids
            if len(cids):
                getPrintChildren(req, c, ret)

    return ret


RE_PRINT_URL = re.compile("/print/(\d+).pdf")


def redirect_old_printview(req):
    req.reply_headers["Location"] = req.path + ".pdf"
    return httpstatus.HTTP_TEMPORARY_REDIRECT


def show_printview(req):
    """ create a pdf preview of given node (id in path e.g. /print/[id].pdf)"""
    match = RE_PRINT_URL.match(req.path)
    nodeid = int(match.group(1))

    node = q(Node).get(nodeid)
    if node.system_attrs.get("print") == "0" or not node.has_read_access():
        return 404

    style = int(req.params.get("style", 2))

    # nodetype
    mtype = node.metadatatype

    mask = None
    metadata = None
    if mtype:
        for m in mtype.getMasks():
            if m.getMasktype() == "fullview":
                mask = m
            if m.getMasktype() == "printview":
                mask = m
                break

        if not mask:
            mask = mtype.getMask("nodebig")

        if mask:
            metadata = mask.getViewHTML([node], VIEW_DATA_ONLY + VIEW_HIDE_EMPTY)

    if not metadata:
        metadata = [['nodename', node.getName(), 'Name', 'text']]

    # XXX: use scalar() after duplicate cleanup
    presentation_file = node.files.filter_by(filetype=u"presentation").first()
    imagepath = presentation_file.abspath if presentation_file is not None else None

    # children
    children = []
    if isinstance(node, Container):
        ret = []
        getPrintChildren(req, node, ret)
        logg.debug("getPrintChildren done")

        maskcache = {}

        for c in ret:
            if not isinstance(c, Container):
                # items
                if c.schema in maskcache:
                    c_mask = maskcache[c.schema]
                else:
                    c_mtype = c.metadatatype
                    c_mask = c_mtype.getMask("printlist")
                    if not c_mask:
                        c_mask = c_mtype.getMask("nodesmall")
                    maskcache[c.schema] = c_mask
                _c = c_mask.getViewHTML([c], VIEW_DATA_ONLY)
                if len(_c) > 0:
                    children.append(_c)
            else:
                # header
                items = getPaths(c)
                if not items:
                    continue
                p = []
                for item in items[0]:
                    p.append(item.getName())
                p.append(c.getName())
                children.append([(c.id, " > ".join(p[1:]), c.getName(), "header")])

        if len(children) > 1:
            col = []
            order = []
            try:
                sort = getCollection(node).get("sortfield")
            except:
                logg.exception("exception in show_printview, getting sortfield failed, setting sort = \"\"")
                sort = ""

            for i in range(0, 2):
                col.append((0, ""))
                order.append(1)
                if req.params.get("sortfield" + str(i)) != "":
                    sort = req.params.get("sortfield" + unicode(i), sort)

                if sort != "":
                    if sort.startswith("-"):
                        sort = sort[1:]
                        order[i] = -1
                    _i = 0
                    for c in children[0]:
                        if c[0] == sort:
                            col[i] = (_i, sort)
                        _i += 1
                if col[i][1] == "":
                    col[i] = (0, children[0][0][0])

            # sort method for items
            def myCmp(x, y, col, order):
                cx = ""
                cy = ""
                for item in x:
                    if item[0] == col[0][1]:
                        cx = item[1]
                        break
                for item in y:
                    if item[0] == col[0][1]:
                        cy = item[1]
                        break
                if cx.lower() > cy.lower():
                    return 1 * order[0]
                return -1 * order[0]

            sorted_children = []
            tmp = []
            for item in children:
                if item[0][3] == "header":
                    if len(tmp) > 0:
                        tmp.sort(lambda x, y: myCmp(x, y, col, order))
                        sorted_children.extend(tmp)
                    tmp = []
                    sorted_children.append(item)
                else:
                    tmp.append(item)
            tmp.sort(lambda x, y: myCmp(x, y, col, order))
            sorted_children.extend(tmp)
            children = sorted_children

    print_dir = []
    printfile = printview.getPrintView(lang(req), imagepath, metadata, getPaths(node), style, children, getCollection(node),
                                       return_file=True, print_dir = print_dir)
    _sendFile(req, printfile, "application/pdf", nginx_x_accel_redirect_enabled=False)
    if print_dir:
        shutil.rmtree(print_dir[0], ignore_errors=True)


# use popup method of  metadatatype
def popup_metatype(req):
    mtype = getMetadataType(req.path.split("/")[-1])
    if mtype and hasattr(mtype, "getPopup"):
        mtype.getPopup(req)
    else:
        logg.error("error, no popup method found")
