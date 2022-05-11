#! /usr/bin/python3
# Created by Lukas H Langøy
# 2022-05-11

import typing
import pprint
from typing import List, Dict
import requests
from dataclasses import dataclass
import dataclasses
import json
import whois

pp = pprint.PrettyPrinter(indent=4)
npm_info_api_url = "https://api.npms.io/v2/package/"

start_point = "create-react-app"


class EnhancedJSONEncoder(json.JSONEncoder):

    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


@dataclass
class Package():
    """This will represent a single npm package"""
    name: str
    isFetched: bool
    metadata: str
    maintainers: List[str]
    dependencies: List[str]


@dataclass
class EmailDomain():
    """ This is used to check the domains of the maintainsers"""
    name: str
    isValid: bool


dependency_graph: Dict[str, Package] = {}

email_domain: Dict[str, EmailDomain] = {}

queued_packages: List[str] = []


def get_info(package_name: str):
    global npm_info_api_url
    global dependency_graph
    global email_domain
    global queued_packages

    if (package_name in dependency_graph):
        package = dependency_graph[package_name]
        if package.isFetched:
            return

    response = requests.request("GET", npm_info_api_url + package_name)

    data = response.json()

    maintainers = []
    dependencies: List[str] = []
    try:
        maintainers.append(data['collected']['metadata']['publisher']['email'])
    except KeyError:
        pass

    try:
        for maintainer in data['collected']['metadata']['maintainers']:
            if "email" in maintainer:
                maintainers.append(maintainer['email'])
    except KeyError:
        pass

    try:
        for dep in data['collected']['metadata']['devDependencies']:
            dependencies.append(dep)
    except KeyError:
        pass

    try:
        for dep in data['collected']['metadata']['dependencies']:
            dependencies.append(dep)
    except KeyError:
        pass

    package = Package(package_name, True, "", maintainers, dependencies)
    dependency_graph[package_name] = package

    for main in package.maintainers:
        try:
            domain = main.split('@')[1]
            if not domain in email_domain:
                isValid = whois.whois(domain).registrar != None
                email_domain[domain] = EmailDomain(domain, isValid)
                if not isValid:
                    print("FOUND INVALID DOMAIN %s on email %s",
                          (domain, main))
        except Exception as e:
            pass

    for dep in package.dependencies:
        if dep not in queued_packages:
            queued_packages.append(dep)

    print("%i/%i -> Cur: \t %s " %
          (len(dependency_graph), len(queued_packages), package_name))
    write_depgraph()

    get_info(queued_packages.pop(0))


def write_depgraph():
    global dependency_graph
    # Serializing json
    json_object = json.dumps(dependency_graph,
                             indent=4,
                             cls=EnhancedJSONEncoder)
    # Writing to sample.json
    with open("npm_registry.json", "w") as outfile:
        outfile.write(json_object)


get_info(start_point)
