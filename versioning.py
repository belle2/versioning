#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Management of software versions and global tags
"""

from distutils.version import LooseVersion


def supported_release(release=None):
    """
    Check whether the given release is supported.
    If release is None or the release is not supported it returns the recommended release.
    """

    supported_releases = ['release-01-00-04', 'release-01-02-11', 'release-02-00-02', 'release-02-01-00']
    supported_light_releases = ['light-02-bremen', 'light-1810-conero', 'light-1811-daisymae']

    # default is latest supported release
    if release is None:
        return supported_releases[-1]

    def basf2_version(release):
        return LooseVersion('.'.join(release.split('-')[1:]))

    # update to next supported release
    if release.startswith('pre'):
        release = release[3:19]
    if release.startswith('release-'):
        for supported in supported_releases:
            if basf2_version(release) <= basf2_version(supported):
                return supported

    # update to next supported light release
    if release.startswith('light-'):
        for supported in supported_light_releases:
            if basf2_version(release) <= basf2_version(supported):
                return supported

    # latest supported release
    return supported_releases[-1]


def recommended_global_tags(release, mc=False, analysis=True, input_tags=[]):
    """
    Determine the recommended set of global tags for the given release, processing task, and tags used for the production of the input data.
    """

    global_tags = []

    data_tags = {'release-01-00-04': 'data_reprocessing-release-01-02-04',
                 'release-01-02-11': 'data_reprocessing-release-01-02-04',
                 'release-02-00-02': None,
                 'light-02-arion': 'data_reprocessing_prod6',
                 'light-1810-conero': 'data_reprocessing_prod6',
                 'light-1811-daisymae': 'data_reprocessing_prod6',
                 }
    data_tag = data_tags.get(supported_release(release), None)
    if data_tag is None:
        return input_tags
    global_tags.append(data_tag)

    if mc:
        pass  # no mc tag yet

    if analysis:
        pass  # no analysis tag yet

    return global_tags


def upload_global_tag(task):
    """
    Get the global tag that is supposed to be used for uploads for the given task.
    """

    if task == 'master':
        return None
    elif task == 'online':
        return 'staging_online'
    elif task == 'data':
        return None
    elif task == 'mc':
        return None
    elif task == 'analysis':
        return None


def jira_global_tag(task):
    """
    Get the dictionary of the jira issue that will be created for a global tag update request.
    For creating a sub-issue the parent key has to be set and the isssuetype id has to be 5.
    The summary can be customized with a format string.
    """

    if task == 'master':
        return None
    elif task == 'online':
        return {
            "project": {"key": "BII"},
            "parent": {"key": "BII-3887"},
            "issuetype": {"id": "5"},
            "assignee": {"name": "tkuhr"},
            "summary": "Online global tag request by {user} at {time}"
            }
    elif task == 'data':
        return None
    elif task == 'mc':
        return None
    elif task == 'analysis':
        return None
