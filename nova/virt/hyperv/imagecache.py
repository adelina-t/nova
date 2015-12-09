# Copyright 2013 Cloudbase Solutions Srl
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Image caching and management.
"""
import os

from os_win import utilsfactory
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import units

from nova import exception
from nova import utils
from nova.virt.hyperv import pathutils
from nova.virt import images

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('use_cow_images', 'nova.virt.driver')


class ImageCache(object):
    def __init__(self):
        self._pathutils = pathutils.PathUtils()
        self._vhdutils = utilsfactory.get_vhdutils()

    def _get_root_vhd_size_gb(self, instance):
        if instance.old_flavor:
            return instance.old_flavor.root_gb
        else:
            return instance.root_gb

    def _resize_and_cache_vhd(self, instance, vhd_path):
        vhd_size = self._vhdutils.get_vhd_size(vhd_path)['VirtualSize']

        root_vhd_size_gb = self._get_root_vhd_size_gb(instance)
        root_vhd_size = root_vhd_size_gb * units.Gi

        root_vhd_internal_size = (
                self._vhdutils.get_internal_vhd_size_by_file_size(
                    vhd_path, root_vhd_size))

        if root_vhd_internal_size < vhd_size:
            raise exception.FlavorDiskSmallerThanImage(
                flavor_size=root_vhd_size, image_size=vhd_size)
        if root_vhd_internal_size > vhd_size:
            path_parts = os.path.splitext(vhd_path)
            resized_vhd_path = '%s_%s%s' % (path_parts[0],
                                            root_vhd_size_gb,
                                            path_parts[1])

            @utils.synchronized(resized_vhd_path)
            def copy_and_resize_vhd():
                if not self._pathutils.exists(resized_vhd_path):
                    try:
                        LOG.debug("Copying VHD %(vhd_path)s to "
                                  "%(resized_vhd_path)s",
                                  {'vhd_path': vhd_path,
                                   'resized_vhd_path': resized_vhd_path})
                        self._pathutils.copyfile(vhd_path, resized_vhd_path)
                        LOG.debug("Resizing VHD %(resized_vhd_path)s to new "
                                  "size %(root_vhd_size)s",
                                  {'resized_vhd_path': resized_vhd_path,
                                   'root_vhd_size': root_vhd_size})
                        self._vhdutils.resize_vhd(resized_vhd_path,
                                                  root_vhd_internal_size,
                                                  is_file_max_size=False)
                    except Exception:
                        with excutils.save_and_reraise_exception():
                            if self._pathutils.exists(resized_vhd_path):
                                self._pathutils.remove(resized_vhd_path)

            copy_and_resize_vhd()
            return resized_vhd_path

    def get_cached_image(self, context, instance):
        image_id = instance.image_ref

        image_type = instance.system_metadata['image_disk_format']

        base_image_dir = self._pathutils.get_base_vhd_dir()
        base_image_path = os.path.join(base_image_dir, image_id)

        @utils.synchronized(base_image_path)
        def fetch_image_if_not_existing():
            image_path = None
            for format_ext in ['vhd', 'vhdx', 'iso']:
                test_path = base_image_path + '.' + format_ext
                if self._pathutils.exists(test_path):
                    image_path = test_path
                    break

            if not image_path:
                try:
                    images.fetch(context, image_id, base_image_path,
                                 instance.user_id,
                                 instance.project_id)
                    if image_type == 'iso':
                        format_ext = 'iso'
                    else:
                        format_ext = self._vhdutils.get_vhd_format(
                            base_image_path)
                    image_path = base_image_path + '.' + format_ext.lower()
                    self._pathutils.rename(base_image_path, image_path)
                except Exception:
                    with excutils.save_and_reraise_exception():
                        if self._pathutils.exists(base_image_path):
                            self._pathutils.remove(base_image_path)

            return image_path

        image_path = fetch_image_if_not_existing()

        if CONF.use_cow_images and image_path.split('.')[-1].lower() == 'vhd':
            # Resize the base VHD image as it's not possible to resize a
            # differencing VHD. This does not apply to VHDX images.
            resized_image_path = self._resize_and_cache_vhd(instance,
                                                            image_path)
            if resized_image_path:
                return resized_image_path

        return image_path
