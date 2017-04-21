# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class PhotoshopCCSceneCollector(HookBaseClass):
    """
    Collector that operates on the photoshop cc active document. Should inherit
    from the basic collector.
    """

    def process_current_session(self, parent_item):
        """
        Analyzes the open documents in Photoshop and creates publish items
        parented under the supplied item.

        :param parent_item: Root item instance
        """

        # go ahead and build the path to the icon for use by any documents
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "photoshop.png"
        )

        # iterate over all open documents and add them as publish items
        engine = self.parent.engine
        for document in engine.adobe.app.documents:

            # create a publish item for the document
            document_item = parent_item.create_item(
                "photoshop.document",
                "Photoshop Image",
                document.name
            )

            document_item.set_icon_from_path(icon_path)

            # add the document object to the properties so that the publish
            # plugins know which open document to associate with this item
            document_item.properties["document"] = document

            self.logger.info(
                "Collected Photoshop document: %s" % (document.name))

        # TODO: only the active document should be enabled
