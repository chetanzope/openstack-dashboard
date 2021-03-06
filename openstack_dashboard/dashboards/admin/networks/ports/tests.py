# Copyright 2012 NEC Corporation
# Copyright 2015 Cisco Systems, Inc.
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

from django import http
from django.urls import reverse

from mox3.mox import IsA

from horizon.workflows import views

from openstack_dashboard import api
from openstack_dashboard.test import helpers as test

DETAIL_URL = 'horizon:admin:networks:ports:detail'

NETWORKS_INDEX_URL = reverse('horizon:admin:networks:index')
NETWORKS_DETAIL_URL = 'horizon:admin:networks:detail'


class NetworkPortTests(test.BaseAdminViewTests):

    @test.create_stubs({api.neutron: ('network_get',
                                      'port_get',
                                      'is_extension_supported',)})
    def test_port_detail(self):
        self._test_port_detail()

    @test.create_stubs({api.neutron: ('network_get',
                                      'port_get',
                                      'is_extension_supported',)})
    def test_port_detail_with_mac_learning(self):
        self._test_port_detail(mac_learning=True)

    def _test_port_detail(self, mac_learning=False):
        port = self.ports.first()
        network_id = self.networks.first().id
        api.neutron.port_get(IsA(http.HttpRequest), port.id)\
            .AndReturn(self.ports.first())
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .MultipleTimes().AndReturn(mac_learning)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'allowed-address-pairs') \
            .MultipleTimes().AndReturn(False)
        api.neutron.network_get(IsA(http.HttpRequest), network_id)\
            .AndReturn(self.networks.first())
        self.mox.ReplayAll()

        res = self.client.get(reverse(DETAIL_URL, args=[port.id]))

        self.assertTemplateUsed(res, 'horizon/common/_detail.html')
        self.assertEqual(res.context['port'].id, port.id)

    @test.create_stubs({api.neutron: ('port_get',)})
    def test_port_detail_exception(self):
        port = self.ports.first()
        api.neutron.port_get(IsA(http.HttpRequest), port.id)\
            .AndRaise(self.exceptions.neutron)

        self.mox.ReplayAll()

        res = self.client.get(reverse(DETAIL_URL, args=[port.id]))

        redir_url = NETWORKS_INDEX_URL
        self.assertRedirectsNoFollow(res, redir_url)

    def test_port_create_get(self):
        self._test_port_create_get()

    def test_port_create_get_with_mac_learning(self):
        self._test_port_create_get(mac_learning=True)

    def test_port_create_get_with_port_security(self):
        self._test_port_create_get(port_security=True)

    @test.create_stubs({api.neutron: ('network_get',
                                      'is_extension_supported',
                                      'security_group_list',)})
    def _test_port_create_get(self, mac_learning=False, binding=False,
                              port_security=False):
        network = self.networks.first()
        api.neutron.network_get(IsA(http.HttpRequest),
                                network.id)\
            .AndReturn(self.networks.first())

        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .AndReturn(mac_learning)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'binding')\
            .AndReturn(binding)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'port-security')\
            .AndReturn(port_security)
        api.neutron.security_group_list(IsA(http.HttpRequest),
                                        tenant_id=None)\
            .AndReturn(self.security_groups.list())
        self.mox.ReplayAll()

        url = reverse('horizon:admin:networks:addport',
                      args=[network.id])
        res = self.client.get(url)

        self.assertTemplateUsed(res, views.WorkflowView.template_name)

    def test_port_create_post(self):
        self._test_port_create_post()

    def test_port_create_post_with_mac_learning(self):
        self._test_port_create_post(mac_learning=True, binding=False)

    def test_port_create_post_with_port_security(self):
        self._test_port_create_post(port_security=True)

    @test.create_stubs({api.neutron: ('network_get',
                                      'is_extension_supported',
                                      'security_group_list',
                                      'port_create',)})
    def _test_port_create_post(self, mac_learning=False, binding=False,
                               port_security=False):
        network = self.networks.first()
        port = self.ports.first()
        security_groups = self.security_groups.list()
        api.neutron.network_get(IsA(http.HttpRequest),
                                network.id)\
            .AndReturn(self.networks.first())
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .AndReturn(mac_learning)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'binding') \
            .AndReturn(binding)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'port-security')\
            .AndReturn(port_security)
        api.neutron.security_group_list(IsA(http.HttpRequest),
                                        tenant_id=None)\
            .AndReturn(self.security_groups.list())
        extension_kwargs = {}
        if binding:
            extension_kwargs['binding__vnic_type'] = \
                port.binding__vnic_type
        if mac_learning:
            extension_kwargs['mac_learning_enabled'] = True
        if port_security:
            extension_kwargs['port_security_enabled'] = True
            extension_kwargs['wanted_groups'] = security_groups
        api.neutron.port_create(IsA(http.HttpRequest),
                                tenant_id=network.tenant_id,
                                network_id=network.id,
                                name=port.name,
                                admin_state_up=port.admin_state_up,
                                device_id=port.device_id,
                                device_owner=port.device_owner,
                                binding__host_id=port.binding__host_id,
                                mac_address=port.mac_address,
                                **extension_kwargs)\
            .AndReturn(port)
        self.mox.ReplayAll()

        form_data = {'network_id': port.network_id,
                     'network_name': network.name,
                     'name': port.name,
                     'admin_state': port.admin_state_up,
                     'device_id': port.device_id,
                     'device_owner': port.device_owner,
                     'binding__host_id': port.binding__host_id,
                     'mac_address': port.mac_address}
        if binding:
            form_data['binding__vnic_type'] = port.binding__vnic_type
        if mac_learning:
            form_data['mac_state'] = True
        if port_security:
            form_data['port_security_enabled'] = True
            form_data['wanted_groups'] = security_groups
        url = reverse('horizon:admin:networks:addport',
                      args=[port.network_id])
        res = self.client.post(url, form_data)

        self.assertNoFormErrors(res)
        redir_url = reverse(NETWORKS_DETAIL_URL, args=[port.network_id])
        self.assertRedirectsNoFollow(res, redir_url)

    @test.create_stubs({api.neutron: ('network_get',
                                      'is_extension_supported',
                                      'security_group_list',
                                      'port_create',)})
    def test_port_create_post_with_fixed_ip(self):
        network = self.networks.first()
        port = self.ports.first()
        api.neutron.network_get(IsA(http.HttpRequest),
                                network.id) \
            .MultipleTimes().AndReturn(self.networks.first())
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .AndReturn(True)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'port-security')\
            .AndReturn(True)
        api.neutron.security_group_list(IsA(http.HttpRequest),
                                        tenant_id=None)\
            .AndReturn(self.security_groups.list())
        extension_kwargs = {}
        extension_kwargs['binding__vnic_type'] = \
            port.binding__vnic_type
        api.neutron.port_create(IsA(http.HttpRequest),
                                tenant_id=network.tenant_id,
                                network_id=network.id,
                                name=port.name,
                                admin_state_up=port.admin_state_up,
                                device_id=port.device_id,
                                device_owner=port.device_owner,
                                binding__host_id=port.binding__host_id,
                                mac_address=port.mac_address,
                                fixed_ips=port.fixed_ips,
                                **extension_kwargs)\
            .AndReturn(port)
        self.mox.ReplayAll()

        form_data = {'network_id': port.network_id,
                     'network_name': network.name,
                     'name': port.name,
                     'admin_state': port.admin_state_up,
                     'device_id': port.device_id,
                     'device_owner': port.device_owner,
                     'binding__host_id': port.binding__host_id,
                     'mac_address': port.mac_address,
                     'specify_ip': 'fixed_ip',
                     'fixed_ip': port.fixed_ips[0]['ip_address'],
                     'subnet_id': port.fixed_ips[0]['subnet_id']}
        form_data['binding__vnic_type'] = port.binding__vnic_type
        form_data['mac_state'] = True
        url = reverse('horizon:admin:networks:addport',
                      args=[port.network_id])
        res = self.client.post(url, form_data)

        self.assertNoFormErrors(res)
        redir_url = reverse(NETWORKS_DETAIL_URL, args=[port.network_id])
        self.assertRedirectsNoFollow(res, redir_url)

    def test_port_create_post_exception(self):
        self._test_port_create_post_exception()

    def test_port_create_post_exception_with_mac_learning(self):
        self._test_port_create_post_exception(mac_learning=True)

    def test_port_create_post_exception_with_port_security(self):
        self._test_port_create_post_exception(port_security=True)

    @test.create_stubs({api.neutron: ('network_get',
                                      'port_create',
                                      'security_group_list',
                                      'is_extension_supported',)})
    def _test_port_create_post_exception(self, mac_learning=False,
                                         binding=False,
                                         port_security=False):
        network = self.networks.first()
        port = self.ports.first()
        security_groups = self.security_groups.list()
        api.neutron.network_get(IsA(http.HttpRequest),
                                network.id)\
            .AndReturn(self.networks.first())
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .AndReturn(mac_learning)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'binding') \
            .AndReturn(binding)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'port-security')\
            .AndReturn(port_security)
        api.neutron.security_group_list(IsA(http.HttpRequest),
                                        tenant_id=None)\
            .AndReturn(self.security_groups.list())
        extension_kwargs = {}
        if binding:
            extension_kwargs['binding__vnic_type'] = port.binding__vnic_type
        if mac_learning:
            extension_kwargs['mac_learning_enabled'] = True
        if port_security:
            extension_kwargs['port_security_enabled'] = True
            extension_kwargs['wanted_groups'] = security_groups
        api.neutron.port_create(IsA(http.HttpRequest),
                                tenant_id=network.tenant_id,
                                network_id=network.id,
                                name=port.name,
                                admin_state_up=port.admin_state_up,
                                device_id=port.device_id,
                                device_owner=port.device_owner,
                                binding__host_id=port.binding__host_id,
                                mac_address=port.mac_address,
                                **extension_kwargs)\
            .AndRaise(self.exceptions.neutron)
        self.mox.ReplayAll()

        form_data = {'network_id': port.network_id,
                     'network_name': network.name,
                     'name': port.name,
                     'admin_state': port.admin_state_up,
                     'mac_state': True,
                     'device_id': port.device_id,
                     'device_owner': port.device_owner,
                     'binding__host_id': port.binding__host_id,
                     'mac_address': port.mac_address}
        if binding:
            form_data['binding__vnic_type'] = port.binding__vnic_type
        if mac_learning:
            form_data['mac_learning_enabled'] = True
        if port_security:
            form_data['port_security_enabled'] = True
            form_data['wanted_groups'] = security_groups
        url = reverse('horizon:admin:networks:addport',
                      args=[port.network_id])
        res = self.client.post(url, form_data)

        self.assertNoFormErrors(res)
        redir_url = reverse(NETWORKS_DETAIL_URL, args=[port.network_id])
        self.assertRedirectsNoFollow(res, redir_url)

    def test_port_update_get(self):
        self._test_port_update_get()

    def test_port_update_get_with_mac_learning(self):
        self._test_port_update_get(mac_learning=True)

    def test_port_update_get_with_port_security(self):
        self._test_port_update_get(port_security=True)

    @test.create_stubs({api.neutron: ('port_get',
                                      'security_group_list',
                                      'is_extension_supported',)})
    def _test_port_update_get(self, mac_learning=False, binding=False,
                              port_security=False):
        port = self.ports.first()
        api.neutron.port_get(IsA(http.HttpRequest),
                             port.id)\
            .AndReturn(port)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'binding') \
            .AndReturn(binding)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .AndReturn(mac_learning)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'port-security')\
            .AndReturn(port_security)
        api.neutron.security_group_list(IsA(http.HttpRequest),
                                        tenant_id=None)\
            .AndReturn(self.security_groups.list())
        self.mox.ReplayAll()

        url = reverse('horizon:admin:networks:editport',
                      args=[port.network_id, port.id])
        res = self.client.get(url)

        self.assertTemplateUsed(res, views.WorkflowView.template_name)

    def test_port_update_post(self):
        self._test_port_update_post()

    def test_port_update_post_with_mac_learning(self):
        self._test_port_update_post(mac_learning=True)

    def test_port_update_post_with_port_security(self):
        self._test_port_update_post(port_security=True)

    @test.create_stubs({api.neutron: ('port_get',
                                      'is_extension_supported',
                                      'security_group_list',
                                      'port_update')})
    def _test_port_update_post(self, mac_learning=False, binding=False,
                               port_security=False):
        port = self.ports.first()
        api.neutron.port_get(IsA(http.HttpRequest), port.id)\
            .AndReturn(port)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'binding')\
            .MultipleTimes().AndReturn(binding)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .MultipleTimes().AndReturn(mac_learning)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'port-security')\
            .MultipleTimes().AndReturn(port_security)
        api.neutron.security_group_list(IsA(http.HttpRequest),
                                        tenant_id=None)\
            .AndReturn(self.security_groups.list())
        extension_kwargs = {}
        if binding:
            extension_kwargs['binding__vnic_type'] = port.binding__vnic_type
        if mac_learning:
            extension_kwargs['mac_learning_enabled'] = True
        if port_security:
            extension_kwargs['port_security_enabled'] = True
        api.neutron.port_update(IsA(http.HttpRequest), port.id,
                                name=port.name,
                                admin_state_up=port.admin_state_up,
                                device_id=port.device_id,
                                device_owner=port.device_owner,
                                binding__host_id=port.binding__host_id,
                                mac_address=port.mac_address,
                                **extension_kwargs)\
            .AndReturn(port)
        self.mox.ReplayAll()

        form_data = {'network_id': port.network_id,
                     'port_id': port.id,
                     'name': port.name,
                     'admin_state': port.admin_state_up,
                     'device_id': port.device_id,
                     'device_owner': port.device_owner,
                     'binding__host_id': port.binding__host_id,
                     'mac_address': port.mac_address}

        if binding:
            form_data['binding__vnic_type'] = port.binding__vnic_type
        if mac_learning:
            form_data['mac_state'] = True
        if port_security:
            form_data['port_security_enabled'] = True
        url = reverse('horizon:admin:networks:editport',
                      args=[port.network_id, port.id])
        res = self.client.post(url, form_data)

        redir_url = reverse(NETWORKS_DETAIL_URL, args=[port.network_id])
        self.assertRedirectsNoFollow(res, redir_url)

    def test_port_update_post_exception(self):
        self._test_port_update_post_exception()

    def test_port_update_post_exception_with_mac_learning(self):
        self._test_port_update_post_exception(mac_learning=True, binding=False)

    def test_port_update_post_exception_with_port_security(self):
        self._test_port_update_post_exception(port_security=True)

    @test.create_stubs({api.neutron: ('port_get',
                                      'is_extension_supported',
                                      'security_group_list',
                                      'port_update')})
    def _test_port_update_post_exception(self, mac_learning=False,
                                         binding=False,
                                         port_security=False):
        port = self.ports.first()
        api.neutron.port_get(IsA(http.HttpRequest), port.id)\
            .AndReturn(port)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'binding')\
            .MultipleTimes().AndReturn(binding)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .MultipleTimes().AndReturn(mac_learning)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'port-security')\
            .MultipleTimes().AndReturn(port_security)
        api.neutron.security_group_list(IsA(http.HttpRequest),
                                        tenant_id=None)\
            .AndReturn(self.security_groups.list())
        extension_kwargs = {}
        if binding:
            extension_kwargs['binding__vnic_type'] = port.binding__vnic_type
        if mac_learning:
            extension_kwargs['mac_learning_enabled'] = True
        if port_security:
            extension_kwargs['port_security_enabled'] = True
        api.neutron.port_update(IsA(http.HttpRequest), port.id,
                                name=port.name,
                                admin_state_up=port.admin_state_up,
                                device_id=port.device_id,
                                device_owner=port.device_owner,
                                binding__host_id=port.binding__host_id,
                                mac_address=port.mac_address,
                                **extension_kwargs)\
            .AndRaise(self.exceptions.neutron)
        self.mox.ReplayAll()

        form_data = {'network_id': port.network_id,
                     'port_id': port.id,
                     'name': port.name,
                     'admin_state': port.admin_state_up,
                     'device_id': port.device_id,
                     'device_owner': port.device_owner,
                     'binding__host_id': port.binding__host_id,
                     'mac_address': port.mac_address}
        if binding:
            form_data['binding__vnic_type'] = port.binding__vnic_type
        if mac_learning:
            form_data['mac_state'] = True
        if port_security:
            form_data['port_security_enabled'] = True
        url = reverse('horizon:admin:networks:editport',
                      args=[port.network_id, port.id])
        res = self.client.post(url, form_data)

        redir_url = reverse(NETWORKS_DETAIL_URL, args=[port.network_id])
        self.assertRedirectsNoFollow(res, redir_url)

    @test.create_stubs({api.neutron: ('port_delete',
                                      'subnet_list',
                                      'port_list',
                                      'show_network_ip_availability',
                                      'is_extension_supported',
                                      'list_dhcp_agent_hosting_networks',)})
    def test_port_delete(self):
        self._test_port_delete()

    @test.create_stubs({api.neutron: ('port_delete',
                                      'subnet_list',
                                      'port_list',
                                      'show_network_ip_availability',
                                      'is_extension_supported',
                                      'list_dhcp_agent_hosting_networks',)})
    def test_port_delete_with_mac_learning(self):
        self._test_port_delete(mac_learning=True)

    def _test_port_delete(self, mac_learning=False):
        port = self.ports.first()
        network_id = port.network_id
        api.neutron.port_list(IsA(http.HttpRequest), network_id=network_id)\
            .AndReturn([self.ports.first()])
        api.neutron.is_extension_supported(
            IsA(http.HttpRequest),
            'network-ip-availability').AndReturn(True)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .AndReturn(mac_learning)
        self.mox.ReplayAll()

        form_data = {'action': 'ports__delete__%s' % port.id}
        url = reverse(NETWORKS_DETAIL_URL, args=[network_id])
        res = self.client.post(url, form_data)

        self.assertRedirectsNoFollow(res, url)

    @test.create_stubs({api.neutron: ('port_delete',
                                      'subnet_list',
                                      'port_list',
                                      'show_network_ip_availability',
                                      'is_extension_supported',
                                      'list_dhcp_agent_hosting_networks',)})
    def test_port_delete_exception(self):
        self._test_port_delete_exception()

    @test.create_stubs({api.neutron: ('port_delete',
                                      'subnet_list',
                                      'port_list',
                                      'show_network_ip_availability',
                                      'is_extension_supported',
                                      'list_dhcp_agent_hosting_networks')})
    def test_port_delete_exception_with_mac_learning(self):
        self._test_port_delete_exception(mac_learning=True)

    def _test_port_delete_exception(self, mac_learning=False):
        port = self.ports.first()
        network_id = port.network_id
        api.neutron.port_delete(IsA(http.HttpRequest), port.id)\
            .AndRaise(self.exceptions.neutron)
        api.neutron.port_list(IsA(http.HttpRequest), network_id=network_id)\
            .AndReturn([self.ports.first()])
        api.neutron.is_extension_supported(
            IsA(http.HttpRequest),
            'network-ip-availability').AndReturn(True)
        api.neutron.is_extension_supported(IsA(http.HttpRequest),
                                           'mac-learning')\
            .AndReturn(mac_learning)
        self.mox.ReplayAll()

        form_data = {'action': 'ports__delete__%s' % port.id}
        url = reverse(NETWORKS_DETAIL_URL, args=[network_id])
        res = self.client.post(url, form_data)

        self.assertRedirectsNoFollow(res, url)
