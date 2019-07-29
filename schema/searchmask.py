import hashlib
import random
from sqlalchemy import func
from . import schema
from core.postgres import check_type_arg
from core import Node
from core import db
from core.systemtypes import Root, Searchmasks
from .schema import Metadatatype

q = db.query

class SearchMask(Node):
    pass

@check_type_arg
class SearchMaskItem(Node):

    def getFirstField(self):
        if len(self.children):
            return self.children[0]
        return None


def newMask(node):
    searchmask_root = q(Searchmasks).one()
    while True:
        maskname = unicode(hashlib.md5(ustr(random.random())).hexdigest()[0:8])
        if maskname in searchmask_root.children.all():
            continue
        else:
            break
    mask = Node(name=maskname, type=u"searchmask")
    searchmask_root.children.append(mask)
    node.set("searchmaskname", maskname)
    return mask


def getMask(node):
    maskname = node.get("searchmaskname")
    mask = q(Searchmasks).one().children.filter_by(name=maskname).scalar()
    if not maskname or mask is None:
        return newMask(node)
    else:
        return mask


def getMainContentType(node):
    #todo this needs acl checks

    occurrence = node.all_children_by_query(
        q(Node.schema, func.count(Node.schema)).group_by(Node.schema).order_by(func.count(Node.schema).desc()))

    for schema_name, count in occurrence:
        metadatatype = q(Metadatatype).filter_by(name=schema_name).filter(Metadatatype.a.active == "1").filter_read_access().first()
        if metadatatype:
            return metadatatype
    return None


def generateMask(node):
    mask = getMask(node)

    maintype = getMainContentType(node)
    if not maintype:
        return

    # clean up
    for field in mask.children:
        mask.children.remove(field)

    #todo this also needs to be fixed
    allfields_parent = maintype
    allfields = maintype.metafields.all()
    allfieldnames = [mf.name for mf in allfields]

    for metafield in maintype.getMetaFields("s"):
        d = metafield.get("label")
        if not d:
            d = metafield.getName()
        new_maskitem = Node(d, type="searchmaskitem")
        mask.children.append(new_maskitem)
        if metafield.get("type") == "union":
            for t in metafield.get("valuelist").split(";"):
                if t and t in allfieldnames:
                    new_maskitem.children.append(allfields_parent.children.filter_by(name=t).one())
        else:
            new_maskitem.children.append(metafield)

    db.session.commit()
    return mask