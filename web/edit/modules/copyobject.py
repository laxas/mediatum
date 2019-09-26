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

from web.edit.edit import get_ids_from_req as _get_ids_from_req
from contenttypes import Data as _Data
from core import db as _db

_q = _db.query

def getContent(req, ids):

    _node = _q(_Data).get(long(ids[0]))

    return req.getTAL("web/edit/modules/movecopyobject.html", {'id': _node.id, 'action': 'copy'}, macro="view_node")
