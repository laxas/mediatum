# -*- coding: utf-8 -*-
"""
 mediatum - a multimedia content repository

 Copyright (C) 2011 Arne Seifert <arne.seifert@tum.de>

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

from .upload import WorkflowStep
from .workflow import registerStep
from core.translation import t, addLabels
from utils.utils import isNumeric
from core import Node
from core import db
import json
from schema.schema import Metafield
from contenttypes.container import Directory

q = db.query


def register():
    registerStep("workflowstep_addtofolder")
    addLabels(WorkflowStep_AddToFolder.getLabels())


class WorkflowStep_AddToFolder(WorkflowStep):

    """
        workflowstep that adds item to selectable subfolder.
        attributes:
            - destination: list of node ids ;-separated
            - subfolder: list of subfolders below destination, if a subfolder exists the item is added and the remaining
                         subfolders are ignored
                         subfolders are specified as json-string and can contain metadata from the item, like:
                         ["{faculty}/Prüfungsarbeiten/{type}en/", "{faculty}/Prüfungsarbeiten/Weitere Prüfungsarbeiten/"]
                    
    """

    def show_workflow_node(self, node, req):
        return self.forwardAndShow(node, True, req)

    def getFolder(self, node, destNode, subfolder):
        """
        search the subfolder below destNode
        :param node: node which should be placed in the subfolder, parts of the node attributes may be specified
                    in subfolder
        :param destNode: destination Node under which the subfolder is searched
        :param subfolder: directorypath to the subfolder below destNode like: "{faculty}/Prüfungsarbeiten/{type}en/"
        :return: returns the node if the subfolder if found or None
        """

        subfolderNode = destNode
        for subdir in subfolder.format(**node.attrs).split("/"):
            if not subdir:
                continue
            subfolderNode = subfolderNode.children.filter_by(name=subdir).scalar()
            if not subfolderNode:
                return None

        return subfolderNode

    def runAction(self, node, op=""):
        subfolders = json.loads(self.get('destination_subfolder'))

        for nid in self.get('destination').split(";"):
            if not nid:
                continue
            destNode = q(Node).get(nid)
            if not destNode:
                continue

            for subfolder in subfolders:
                subfolderNode = self.getFolder(node, destNode, subfolder)
                if not subfolderNode:
                    continue

                subfolderNode.children.append(node)
                db.session.commit()
                break

    def metaFields(self, lang=None):
        ret = []
        field = Metafield("destination")
        field.set("label", t(lang, "admin_wfstep_addtofolder_destination"))
        field.set("type", "treeselect")
        ret.append(field)
        field = Metafield("destination_subfolder")
        field.set("label", t(lang, "admin_wfstep_addtofolder_destination_subfolder"))
        field.set("type", "text")
        ret.append(field)
        return ret

    @staticmethod
    def getLabels():
        return {"de":
                [
                    ("workflowstep-addtofolder", "Zu einem Verzeichnis hinzufügen"),
                    ("admin_wfstep_addtofolder_destination", "Zielknoten-ID"),
                    ("admin_wfstep_addtofolder_destination_subfolder", "Unterverzeichnis"),
                ],
                "en":
                [
                    ("workflowstep-addtofolder", "add to folder"),
                    ("admin_wfstep_addtofolder_destination", "ID of destination node"),
                    ("admin_wfstep_addtofolder_destination_subfolder", "sub folder"),
                ]
                }
