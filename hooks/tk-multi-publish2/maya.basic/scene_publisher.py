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


class MayaScenePublishPlugin(HookBaseClass):
    """
    Plugin for publishing an open maya scene. Should inherit from the maya file
    publisher.
    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "publish.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish Maya Scene"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return """
        Publishes the current maya scene.

        This plugin will recognize version numbers in the file name and will
        publish with that version number to Shotgun. If the "Auto Version"
        setting is enabled, the plugin will automatically copy the file to the
        next version number after publishing.
        """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        return {
            "Publish Type": {
                "type": "shotgun_publish_type",
                "default": "Maya Scene",
                "description": "SG publish type to associate publishes with."
            },
            "Auto Version": {
                "type": "bool",
                "default": True,
                "description": (
                    "If set to True, the file will be automatically saved to "
                    "the next version after publish."
                )
            },
            # TODO: revisit default states for settings ^
        }

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["maya.scene"]

    def accept(self, log, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                        all.
            - required: If set to True, the publish task is required and cannot
                        be disabled.
            - enabled:  If True, the publish task will be enabled in the UI by
                        default.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        # if we have a project root, check for a valid, serialized context.
        # warn if not.
        if "project_root" in item.properties:

            project_root = item.properties["project_root"]
            context_file = os.path.join(project_root, "shotgun.context")

            log.debug("Looking for context file in %s" % context_file)
            if os.path.exists(context_file):
                try:
                    with open(context_file, "rb") as fh:
                        context_str = fh.read()
                    context_obj = sgtk.Context.deserialize(context_str)
                    item.context = context_obj
                except Exception, e:
                    log.warning(
                        "Could not read saved context %s: %s" %
                        (context_file, e)
                    )

        return {"accepted": True, "required": False, "enabled": True}

    def validate(self, log, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity. Use the logger to output further details
        around why validation has failed.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        # get the path to the current file
        path = cmds.file(query=True, sn=True)

        if not path:
            log.error("Scene is not saved.")
            return False

        # ensure we have an updated project root
        project_root = cmds.workspace(q=True, rootDirectory=True)
        item.properties["project_root"] = project_root

        # warn if no project root could be determined.
        if not project_root:
            log.warning("Your scene is not part of a maya project.")

        publisher = self.parent

        # get the publish name for this file path. this will ensure we get a
        # consistent publish name when looking up existing publishes.
        publish_name = publisher.util.get_publish_name(path)

        log.info("Publish name will be: %s" % (publish_name,))

        # see if there are any other publishes of this path with a status.
        # Note the name, context, and path *must* match the values supplied to
        # register_publish in the publish phase in order for this to return an
        # accurate list of previous publishes of this file.
        publishes = publisher.util.get_conflicting_publishes(
            item.context,
            path,
            publish_name,
            filters=["sg_status_list", "is_not", None]
        )

        if publishes:
            log.warn(
                "Found %s conflicting publishes in Shotgun with the path '%s'. "
                "If you continue, these conflicting publishes will no longer "
                "be available to other users via the loader." %
                (len(publishes), path)
            )

        return True

    def publish(self, log, settings, item):
        """
        Executes the publish logic for the given item and settings. Use the
        logger to give the user status updates.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # get the path to the current file
        path = cmds.file(query=True, sn=True)

        publisher = self.parent

        # get the publish name for this file path. this will ensure we get a
        # consistent name across version publishes of this file.
        publish_name = publisher.util.get_publish_name(path)

        # extract the version number for publishing. use 1 if no version in path
        version_number = publisher.util.get_version_number(path) or 1

        # arguments for publish registration
        args = {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": path,
            "name": publish_name,
            "version_number": version_number,
            "thumbnail_path": item.get_thumbnail_as_path(),
            "published_file_type": settings["Publish Type"].value,
            # TODO: need to update core for this to work
            #"dependency_paths": self._maya_find_additional_scene_dependencies(),
        }
        log.debug("Publishing: %s" % (args,))

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties["sg_publish_data"] = sgtk.util.register_publish(**args)

        # now that we've published. keep a handle on the path that was published
        item.properties["path"] = path

    def finalize(self, log, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param log: Logger to output feedback to.
        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # try to save the associated context into the project root. since the
        # project root isn't required, bail if not known.
        if "project_root" in item.properties:
            project_root = item.properties["project_root"]
            context_file = os.path.join(project_root, "shotgun.context")
            with open(context_file, "wb") as fh:
                fh.write(item.context.serialize(with_user_credentials=False))

        publisher = self.parent

        # get the path to the file
        path = item.properties["path"]

        # get the data for the publish that was just created in SG
        publish_data = item.properties["sg_publish_data"]

        # ensure conflicting publishes have their status cleared
        log.info("Clearing status of conflicting publishes...")
        publisher.util.clear_status_for_conflicting_publishes(
            item.context, publish_data)

        # do the auto versioning if it is enabled
        if settings["Auto Version"].value:
            version_info = publisher.util.create_next_version_path(path)
            if version_info["success"]:
                log.info(
                    "Copied %s to %s." %
                    (path, version_info["next_version_path"])
                )
            else:
                reason = version_info["reason"]
                log.warn("Unable to Auto Version. %s" % (reason,))

    def _maya_find_additional_scene_dependencies(self):
        """
        Find additional dependencies from the scene
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
            # ensure this is actually part of this scene and not referenced
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
