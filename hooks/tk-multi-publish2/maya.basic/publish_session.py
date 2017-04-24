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
import maya.cmds as cmds
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class MayaPublishSessionPlugin(HookBaseClass):
    """
    Plugin for publishing an open maya session. This plugin must inherit from
    the basic session publisher. It implements the maya specific components
    required by that plugin's abstract api. For specifics about how the plugin
    works, see the publish phase implementations in the base class.
    """

    @property
    def publish_type(self):
        """
        The publish type to use when publishing matched items.
        :return:
        """
        return "Maya Scene"

    @property
    def session_path(self):
        """
        Returns the path to the current
        :return:
        """
        return cmds.file(query=True, sn=True)

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["maya.session"]

    @property
    def session_dependency_paths(self):
        """
        A list of updstream dependencies referenced in the session.
        """

        # default implementation looks for references and
        # textures (file nodes) and returns any paths that
        # match a template defined in the configuration
        ref_paths = set()

        # first let's look at maya references
        ref_nodes = cmds.ls(references=True)
        for ref_node in ref_nodes:
            # get the path:
            ref_path = cmds.referenceQuery(ref_node, filename=True)
            # make it platform dependent
            # (maya uses C:/style/paths)
            ref_path = ref_path.replace("/", os.path.sep)
            if ref_path:
                ref_paths.add(ref_path)

        # now look at file texture nodes
        for file_node in cmds.ls(l=True, type="file"):
            # ensure this is actually part of this session and not referenced
            if cmds.referenceQuery(file_node, isNodeReferenced=True):
                # this is embedded in another reference, so don't include it in
                # the breakdown
                continue

            # get path and make it platform dependent
            # (maya uses C:/style/paths)
            texture_path = cmds.getAttr(
                "%s.fileTextureName" % file_node).replace("/", os.path.sep)
            if texture_path:
                ref_paths.add(texture_path)

        return ref_paths
