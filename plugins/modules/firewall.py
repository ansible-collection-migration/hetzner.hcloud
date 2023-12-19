#!/usr/bin/python

# Copyright: (c) 2020, Hetzner Cloud GmbH <info@hetzner-cloud.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import annotations

DOCUMENTATION = """
---
module: firewall
short_description: Create and manage firewalls on the Hetzner Cloud.

description:
    - Create, update and manage firewalls on the Hetzner Cloud.

author:
    - Lukas Kaemmerling (@lkaemmerling)

options:
    id:
        description:
            - The ID of the Hetzner Cloud Firewall to manage.
            - Only required if no firewall O(name) is given.
        type: int
    name:
        description:
            - The Name of the Hetzner Cloud Firewall to manage.
            - Only required if no firewall O(id) is given, or the firewall does not exist.
        type: str
    labels:
        description:
            - User-defined labels (key-value pairs).
        type: dict
    rules:
        description:
            - List of rules the firewall contain.
        type: list
        elements: dict
        suboptions:
            description:
                description:
                    - User defined description of this rule.
                type: str
            direction:
                description:
                    - The direction of the firewall rule.
                type: str
                choices: [in, out]
            protocol:
                description:
                    - The protocol of the firewall rule.
                type: str
                choices: [icmp, tcp, udp, esp, gre]
            port:
                description:
                    - The port or port range allowed by this rule.
                    - A port range can be specified by separating two ports with a dash, e.g 1024-5000.
                    - Only used if O(rules[].protocol=tcp) or O(rules[].protocol=udp).
                type: str
            source_ips:
                description:
                    - List of CIDRs that are allowed within this rule.
                    - Use 0.0.0.0/0 to allow all IPv4 addresses and ::/0 to allow all IPv6 addresses.
                    - Only used if O(rules[].direction=in).
                type: list
                elements: str
                default: []
            destination_ips:
                description:
                    - List of CIDRs that are allowed within this rule.
                    - Use 0.0.0.0/0 to allow all IPv4 addresses and ::/0 to allow all IPv6 addresses.
                    - Only used if O(rules[].direction=out).
                type: list
                elements: str
                default: []
    state:
        description:
            - State of the firewall.
        default: present
        choices: [absent, present]
        type: str

extends_documentation_fragment:
    - hetzner.hcloud.hcloud
"""

EXAMPLES = """
- name: Create a basic firewall
  hetzner.hcloud.firewall:
    name: my-firewall
    state: present

- name: Create a firewall with rules
  hetzner.hcloud.firewall:
    name: my-firewall
    rules:
      - description: allow icmp from everywhere
        direction: in
        protocol: icmp
        source_ips:
          - 0.0.0.0/0
          - ::/0
    state: present

- name: Create a firewall with labels
  hetzner.hcloud.firewall:
    name: my-firewall
    labels:
      key: value
      mylabel: 123
    state: present

- name: Ensure the firewall is absent (remove if needed)
  hetzner.hcloud.firewall:
    name: my-firewall
    state: absent
"""

RETURN = """
hcloud_firewall:
    description: The firewall instance.
    returned: always
    type: dict
    contains:
        id:
            description: Numeric identifier of the firewall.
            returned: always
            type: int
            sample: 1937415
        name:
            description: Name of the firewall.
            returned: always
            type: str
            sample: my-firewall
        labels:
            description: User-defined labels (key-value pairs).
            returned: always
            type: dict
        rules:
            description: List of rules the firewall contain.
            returned: always
            type: list
            elements: dict
            contains:
                description:
                    description: User defined description of this rule.
                    type: str
                    returned: always
                    sample: allow http from anywhere
                direction:
                    description: The direction of the firewall rule.
                    type: str
                    returned: always
                    sample: in
                protocol:
                    description: The protocol of the firewall rule.
                    type: str
                    returned: always
                    sample: tcp
                port:
                    description: The port or port range allowed by this rule.
                    type: str
                    returned: if RV(hcloud_firewall.rules[].protocol=tcp) or RV(hcloud_firewall.rules[].protocol=udp)
                    sample: "80"
                source_ips:
                    description: List of source CIDRs that are allowed within this rule.
                    type: list
                    elements: str
                    returned: always
                    sample: ["0.0.0.0/0", "::/0"]
                destination_ips:
                    description: List of destination CIDRs that are allowed within this rule.
                    type: list
                    elements: str
                    returned: always
                    sample: []
"""

import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native

from ..module_utils.hcloud import AnsibleHCloud
from ..module_utils.vendor.hcloud import APIException, HCloudException
from ..module_utils.vendor.hcloud.firewalls import BoundFirewall, FirewallRule


class AnsibleHCloudFirewall(AnsibleHCloud):
    represent = "hcloud_firewall"

    hcloud_firewall: BoundFirewall | None = None

    def _prepare_result(self):
        return {
            "id": to_native(self.hcloud_firewall.id),
            "name": to_native(self.hcloud_firewall.name),
            "rules": [self._prepare_result_rule(rule) for rule in self.hcloud_firewall.rules],
            "labels": self.hcloud_firewall.labels,
        }

    def _prepare_result_rule(self, rule):
        return {
            "direction": rule.direction,
            "protocol": to_native(rule.protocol),
            "port": to_native(rule.port) if rule.port is not None else None,
            "source_ips": [to_native(cidr) for cidr in rule.source_ips],
            "destination_ips": [to_native(cidr) for cidr in rule.destination_ips],
            "description": to_native(rule.description) if rule.description is not None else None,
        }

    def _get_firewall(self):
        try:
            if self.module.params.get("id") is not None:
                self.hcloud_firewall = self.client.firewalls.get_by_id(self.module.params.get("id"))
            elif self.module.params.get("name") is not None:
                self.hcloud_firewall = self.client.firewalls.get_by_name(self.module.params.get("name"))

        except HCloudException as exception:
            self.fail_json_hcloud(exception)

    def _create_firewall(self):
        self.module.fail_on_missing_params(required_params=["name"])
        params = {
            "name": self.module.params.get("name"),
            "labels": self.module.params.get("labels"),
        }
        rules = self.module.params.get("rules")
        if rules is not None:
            params["rules"] = [
                FirewallRule(
                    direction=rule["direction"],
                    protocol=rule["protocol"],
                    source_ips=rule["source_ips"] if rule["source_ips"] is not None else [],
                    destination_ips=rule["destination_ips"] if rule["destination_ips"] is not None else [],
                    port=rule["port"],
                    description=rule["description"],
                )
                for rule in rules
            ]
        if not self.module.check_mode:
            try:
                self.client.firewalls.create(**params)
            except HCloudException as exception:
                self.fail_json_hcloud(exception, params=params)
        self._mark_as_changed()
        self._get_firewall()

    def _update_firewall(self):
        name = self.module.params.get("name")
        if name is not None and self.hcloud_firewall.name != name:
            self.module.fail_on_missing_params(required_params=["id"])
            if not self.module.check_mode:
                self.hcloud_firewall.update(name=name)
            self._mark_as_changed()

        labels = self.module.params.get("labels")
        if labels is not None and self.hcloud_firewall.labels != labels:
            if not self.module.check_mode:
                self.hcloud_firewall.update(labels=labels)
            self._mark_as_changed()

        rules = self.module.params.get("rules")
        if rules is not None and rules != [self._prepare_result_rule(rule) for rule in self.hcloud_firewall.rules]:
            if not self.module.check_mode:
                new_rules = [
                    FirewallRule(
                        direction=rule["direction"],
                        protocol=rule["protocol"],
                        source_ips=rule["source_ips"] if rule["source_ips"] is not None else [],
                        destination_ips=rule["destination_ips"] if rule["destination_ips"] is not None else [],
                        port=rule["port"],
                        description=rule["description"],
                    )
                    for rule in rules
                ]
                self.hcloud_firewall.set_rules(new_rules)
            self._mark_as_changed()
        self._get_firewall()

    def present_firewall(self):
        self._get_firewall()
        if self.hcloud_firewall is None:
            self._create_firewall()
        else:
            self._update_firewall()

    def delete_firewall(self):
        self._get_firewall()
        if self.hcloud_firewall is not None:
            if not self.module.check_mode:
                retry_count = 0
                while retry_count < 10:
                    try:
                        self.client.firewalls.delete(self.hcloud_firewall)
                        break
                    except APIException as exception:
                        if "is still in use" in exception.message:
                            retry_count = retry_count + 1
                            time.sleep(0.5 * retry_count)
                        else:
                            self.fail_json_hcloud(exception)
                    except HCloudException as exception:
                        self.fail_json_hcloud(exception)
            self._mark_as_changed()
        self.hcloud_firewall = None

    @classmethod
    def define_module(cls):
        return AnsibleModule(
            argument_spec=dict(
                id={"type": "int"},
                name={"type": "str"},
                labels={"type": "dict"},
                rules=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        description={"type": "str"},
                        direction={"type": "str", "choices": ["in", "out"]},
                        protocol={"type": "str", "choices": ["icmp", "udp", "tcp", "esp", "gre"]},
                        port={"type": "str"},
                        source_ips={"type": "list", "elements": "str", "default": []},
                        destination_ips={"type": "list", "elements": "str", "default": []},
                    ),
                    required_together=[["direction", "protocol"]],
                    required_if=[
                        ["protocol", "udp", ["port"]],
                        ["protocol", "tcp", ["port"]],
                    ],
                ),
                state={
                    "choices": ["absent", "present"],
                    "default": "present",
                },
                **super().base_module_arguments(),
            ),
            required_one_of=[["id", "name"]],
            required_if=[["state", "present", ["name"]]],
            supports_check_mode=True,
        )


def main():
    module = AnsibleHCloudFirewall.define_module()

    hcloud = AnsibleHCloudFirewall(module)
    state = module.params.get("state")
    if state == "absent":
        hcloud.delete_firewall()
    elif state == "present":
        hcloud.present_firewall()

    module.exit_json(**hcloud.get_result())


if __name__ == "__main__":
    main()
