# Copyright 2014 Cloudbase Solutions Srl
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

from nova.openstack.common import log as logging
from nova.scheduler import filters

LOG = logging.getLogger(__name__)

# these properties are already handled by image_props_filter.
IGNORE_PROPERTIES = ['architecture', 'hypervisor_type', 'vm_mode']


class ImageExtraResourcesFilter(filters.BaseHostFilter):
    """Filter compute nodes with extra_resources that satisfy instance
    image properties.

    The ImageExtraResourcesFilter filters compute nodes that satisfy
    any properties specified on the instance's image properties, except
    architecture, hypervisor type, or virtual machine mode, as they are
    treated by ImagePropertiesFilter. Image properties are contained in
    the image dictionary in the request_spec.
    """

    # Image Properties do not change within a request.
    run_filter_once_per_request = True

    def _satisfies_extra_resources(self, host_state, image_properties):
        """Checks that the host_state provided by the compute service
        satisfies the extra_resources requirements associated with the
        image_properties.
        """

        properties = {key: req for key, req in image_properties.iteritems()
                      if key not in IGNORE_PROPERTIES}

        if properties and not host_state.extra_resources:
            # instance requires extra_resources that the host doesn't possess.
            return False

        for key, required in properties.iteritems():
            attrib = host_state.extra_resources.get(key, None)
            if not attrib:
                return False

            if isinstance(required, str):
                if isinstance(attrib, list):
                    if required not in attrib:
                        return False
                else:
                    if required != attrib:
                        return False
            elif isinstance(required, int):
                if required > attrib:
                    return False
        return True

    def host_passes(self, host_state, filter_properties):
        """Returns True if the host_state provided has the required
        extra_resources required by the instance, False otherwise."""

        request_spec = filter_properties['request_spec']
        image = request_spec.get('image', None)
        if not image:
            # no image required for the instance
            return True

        image_properties = image.get('properties', None)
        if not image_properties:
            # no extra requirements for the instance.
            return True

        if not self._satisfies_extra_resources(host_state,
                                               image_properties):
            LOG.debug("%(host_state)s fails request_spec extra_resources "
                      "requirements.", {'host_state': host_state})
            return False
        return True
