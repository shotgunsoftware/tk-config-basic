# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from sgtk import Hook


class PickEnvironment(Hook):
    """
    The pick environment hook gets called when Toolkit tries to
    determine which configuration to use. Based on the context
    provided by Toolkit, the name of the environment file to be
    used should be returned by the execute method below.
    """

    def execute(self, context, **kwargs):

        if context.source_entity:
            if context.source_entity["type"] == "Version":
                return "version"
            elif context.source_entity["type"] == "PublishedFile":
                return "publishedfile"
            elif context.source_entity["type"] == "Playlist":
                return "playlist"

        if context.entity and context.step is None:
            # We have an entity but no step.
            if context.entity["type"] == "Shot":
                return "shot"

        if context.entity and context.task:
            # We have an entity and a task.
            if context.entity["type"] == "Shot":
                return "shot_step"
            if context.entity["type"] == "Asset":
                return "asset_step"

        if context.project:
            return "project"

        return "site"
