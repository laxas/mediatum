"""
 mediatum - a multimedia content repository

 Copyright (C) 2009 Arne Seifert <seiferta@in.tum.de>

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

import json

from core import db
from contenttypes import Data, Home, Collection, Collections
from core.systemtypes import Root
from web.edit.edit_common import showdir, shownav, showoperations, default_edit_nodes_per_page,\
    edit_node_per_page_values, searchbox_navlist_height
from web.frontend.frame import render_edit_search_box
from utils.utils import dec_entry_log
from core.translation import translate, lang, t
from schema.schema import get_permitted_schemas
from web.edit.edit import get_ids_from_req
from web.edit.edit_common import get_searchparams, delete_g_nodes_entry
import urllib
import web.common.sort as _sort

q = db.query


def elemInList(elemlist, name):
    for item in elemlist:
        if item.getName() == name:
            return True
    return False


@dec_entry_log
def getContent(req, ids):

    def getDatatypes(_req, _schemes):
        _dtypes = []
        datatypes = Data.get_all_datatypes()
        for scheme in _schemes:
            for dtype in scheme.getDatatypes():
                if dtype not in _dtypes:
                    for _t in datatypes:
#                         if _t.getName() == dtype and not elemInList(dtypes, _t.getName()):
                        dtypes.append(_t)
        _dtypes.sort(lambda x, y: cmp(translate(x.getLongName(), request=_req).lower(), translate(y.getLongName(), request=req).lower()))
        return _dtypes

    def get_ids_from_query():
        ids = get_ids_from_req(req)
        return ",".join(ids)

    node = q(Data).get(long(ids[0]))

    if "action" in req.params:
        if req.params.get('action') == "resort":
            field = req.params.get('value', '').strip()
            res = showdir(req, node, sortfield=field)
            res = json.dumps({'state': 'ok', 'values': res}, ensure_ascii=False)
            req.write(res)
            return None

        elif req.params.get('action') == "save":  # save selection for collection
            field = req.params.get('value')
            if field.strip() == "" or field.strip() == "off":
                if node.get('sortfield'):
                    node.removeAttribute('sortfield')
            else:
                node.set('sortfield', field)
            nodes_per_page = req.params.get('nodes_per_page')
            if nodes_per_page.strip() == "":
                if node.get('nodes_per_page'):
                    node.removeAttribute('nodes_per_page')
            else:
                node.set('nodes_per_page', nodes_per_page)
            req.write(json.dumps({'state': 'ok'}))
            db.session.commit()
        return None

    if node.isContainer():
        schemes = []
        dtypes = []

        item_count = []
        items = showdir(req, node, item_count=item_count)
        nav = shownav(req, node)
        v = {"operations": showoperations(req, node), "items": items, "nav": nav}
        if node.has_write_access():
            schemes = get_permitted_schemas()
            dtypes = getDatatypes(req, schemes)

        if "globalsort" in req.params:
            node.set("sortfield", req.params.get("globalsort"))
        if req.params.get("sortfield", "") != "":
            v['collection_sortfield'] = req.params.get("sortfield")
        else:
            v['collection_sortfield'] = node.get("sortfield")

        if req.params.get("nodes_per_page"):
            v['npp_field'] = req.params.get("nodes_per_page", default_edit_nodes_per_page)
        else:
            v['npp_field'] = node.get("nodes_per_page")
        if not v['npp_field']:
            v['npp_field'] = default_edit_nodes_per_page

        search_html = render_edit_search_box(node, lang(req), req, edit=True)
        searchmode = req.params.get("searchmode")
        navigation_height = searchbox_navlist_height(req, item_count)
        if not isinstance(node, (Root, Collections, Home)):
            sortchoices = _sort.get_sort_choices(container=node,off="off",t_off=t(req, "off"),t_desc=t(req, "descending"))
        else:
            sortchoices = ()

        count = item_count[0] if item_count[0] == item_count[1] else "%d from %d" % (item_count[0], item_count[1])
        v['sortchoices'] = tuple(sortchoices)
        v['types'] = dtypes
        v['schemes'] = schemes
        v['id'] = ids[0]
        v['count'] = count
        v['language'] = lang(req)
        v['search'] = search_html
        v['navigation_height'] = navigation_height
        v['parent'] = node.id
        v['query'] = req.query.replace('id=','src=')
        searchparams = get_searchparams(req)
        searchparams = {k: unicode(v).encode("utf8") for k, v in searchparams.items()}
        v['searchparams'] = urllib.urlencode(searchparams)
        v['get_ids_from_query'] = get_ids_from_query
        v['edit_all_objects'] = t(lang(req), "edit_all_objects").format(item_count[1])
        v['t'] = t
        res = req.getTAL("web/edit/modules/content.html", v, macro="edit_content")
        delete_g_nodes_entry(req)
        return res
    if hasattr(node, "editContentDefault"):
        return node.editContentDefault(req)
    return ""
