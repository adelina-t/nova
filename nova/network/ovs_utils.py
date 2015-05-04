# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

import os

from oslo_config import cfg
from oslo_log import log as logging

from nova import exception
from nova.i18n import _LE
from nova.network import net_common
from nova import utils

LOG = logging.getLogger(__name__)

ovs_cfg = [
    cfg.IntOpt('ovs_vsctl_timeout',
               default=120,
               help='Amount of time, in seconds, that ovs_vsctl should wait '
                    'for a response from the database. 0 is to wait forever.'),
]
CONF = cfg.CONF
CONF.register_opts(ovs_cfg)


def ovs_vsctl(args, run_as_root=True):
    full_args = ['ovs-vsctl', '--timeout=%s' % CONF.ovs_vsctl_timeout] + args
    try:
        return utils.execute(*full_args, run_as_root=run_as_root)
    except Exception as e:
        LOG.error(_LE("Unable to execute %(cmd)s. Exception: %(exception)s"),
                  {'cmd': full_args, 'exception': e})
        raise exception.AgentError(method=full_args)


def create_ovs_vif_port(bridge, dev, iface_id, mac, instance_id, set_mtu=True,
                        run_as_root=True):
    ovs_vsctl(['--', '--if-exists', 'del-port', dev, '--',
                'add-port', bridge, dev,
                '--', 'set', 'Interface', dev,
                'external-ids:iface-id=%s' % iface_id,
                'external-ids:iface-status=active',
                'external-ids:attached-mac=%s' % mac,
                'external-ids:vm-uuid=%s' % instance_id],
                run_as_root=run_as_root)
    if set_mtu is True:
        net_common.set_device_mtu(dev)


def delete_ovs_vif_port(bridge, dev, delete_net_dev=True, run_as_root=True):
    ovs_vsctl(['--', '--if-exists', 'del-port', bridge, dev],
              run_as_root=run_as_root)
    if delete_net_dev is True:
        net_common.delete_net_dev(dev)


def ovs_set_vhostuser_port_type(dev):
    ovs_vsctl(['--', 'set', 'Interface', dev, 'type=dpdkvhostuser'])


def check_bridge_has_dev(bridge, dev, run_as_root=True):
    ports = ovs_vsctl(['--', 'list-ports', bridge],
                       run_as_root=run_as_root)[0]
    return dev in ports.split(os.linesep)
