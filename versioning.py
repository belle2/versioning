#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Management of software versions and global tags
"""

from distutils.version import LooseVersion


# list of supported releases, the last one is the recommended one
_supported_releases = [
    'release-02-00-02', 'release-02-01-00',
    'release-03-01-04', 'release-03-02-03']

# list of supported light releases
_supported_light_releases = [
    'light-1906-firebird', 'light-1907-golfo']


def supported_release(release=None):
    """
    Check whether the given release is supported.

    Parameters:
      release (str): The release version to be checked.
       If release is None the recommended release version is returned.

    Returns:
      The name of the supported release that best matches the release given as input parameter.
    """

    # default is latest supported release
    if release is None:
        return _supported_releases[-1]

    def basf2_version(release):
        return LooseVersion('.'.join(release.split('-')[1:]))

    # update to next supported release
    if release.startswith('pre'):
        release = release[3:19]
    if release.startswith('release-'):
        for supported in _supported_releases:
            if basf2_version(release) <= basf2_version(supported):
                return supported

    # update to next supported light release
    if release.startswith('light-'):
        for supported in _supported_light_releases:
            if basf2_version(release) <= basf2_version(supported):
                return supported

    # latest supported release
    return _supported_releases[-1]


def create_release_html(filename='index.html'):
    """
    Create a html file with the links to the sphinx and doxygen documentations of the supported releses.

    Parameters:
      filename (str): The name the html file.
    """

    page = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" >
<head>
<meta http-equiv="content-type" content="text/html; charset=UTF-8" />
<meta name="keywords" content="Belle II, basf2, documentation, doxygen, sphinx" />
<meta name="description" content="The documentation of the Belle II software." />
<title>Documentation of the Belle II software</title>

<style type="text/css" media="all">
@import "https://b2-master.belle2.org/build_style/index_documentation.css";
</style>

</head>

<body>

<div id="wrap">
<div id="header">
<div id="headerleft"></div>
<div id="headerright"></div>
<div id="topnavigation">
<ul>
<li><a href="http://www.belle2.org">Belle II</a></li>
<li><a href="https://confluence.desy.de/display/BI/Belle+II">Wiki</a></li>
<li><a href="https://stash.desy.de/projects/B2/repos/software/browse">Git</a></li>
<li><a href="https://agira.desy.de/projects/BII">Issues</a></li>
<li><a href="/development_build/index.html">Development Build</a></li>
</ul>
</div>
</div>

<div id="content">

<br/>
<br/>
<div id="resulttable">
<div class="roundbox">
<h2></h2>
<table>
<tbody>
<tr class="odd">
<th>Sphinx documentation</th>
<th>Doxygen documentation</th>
%s
</tbody>
</table>
</div>
<br/>
</div>

</div>
</div>

<div id="footer">
Copyright 2018-2019 Belle II software group <br />
Uses icons from the gnome-colors package under the <a href="http://www.gnu.org/licenses/gpl.html">GNU GENERAL PUBLIC LICENSE</a>
and from http://www.famfamfam.com under the <a href="http://creativecommons.org/licenses/by/2.5/">Creative Commons Attribution 2.5 License</a>
</div>
</body>
</html>
"""
    table = ""
    recommended = ' (recommended)'
    for supported in reversed(_supported_releases):
        table += ('<tr class="even">\n<td><a href="sphinx/%s/index.html"><b>%s%s</b></a></td>\n<td><a href="%s/index.html"><b>%s</b></a></td>\n</tr>\n' % (supported, supported, recommended, supported, supported))
        recommended = ''
    for supported in reversed(_supported_light_releases):
        table += ('<tr class="odd">\n<td><a href="sphinx/%s/index.html"><b>%s</b></a></td>\n<td><a href="%s/index.html"><b>%s</b></a></td>\n</tr>\n' % (supported, supported, supported, supported))
    table += '<tr class="even">\n<td><a href="development/sphinx/index.html"><b>development</b></a></td>\n<td><a href="development/index.html"><b>development</b></a></td>\n</tr>\n'
    with open(filename, 'w') as htmlfile:
        htmlfile.write(page % table)


def recommended_global_tags(release, mc=False, analysis=True, input_tags=[]):
    """
    Determine the recommended set of global tags for the given conditions
    release, processing task, and tags used for the production of the input data.

    Parameters:
      release (str): The release version that the user has set up.
      mc (bool): Whether the MC GT should be added. Used for run-dependent MC.
      analysis (bool): Whether the analysis GT should be added. Used for skimming and analysis.
      input_tags (list): The list of GTs used to produce the input file.

    Returns:
      The list of recommended GTs.
    """

    global_tags = []

    data_tags = {'release-02-00-02': None,
                 'release-02-01-00': None,
                 'release-03-01-04': 'data_reprocessing_proc8',
                 }
    data_tag = data_tags.get(supported_release(release), None)

    # if no tag is explicitly set the default is to take the input GTs
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

    Parameters:
      task (str): An identifier of the task. Supported values are 'master', 'online', 'prompt', data', 'mc', 'analysis'

    Returns:
      The name of the GT for uploads or None if a new GT should be created by the client for each upload request.
    """

    if task == 'master':
        return None
    elif task == 'online':
        return 'staging_online'
    elif task == 'prompt':
        return None
    elif task == 'data':
        return None
    elif task == 'mc':
        return None
    elif task == 'analysis':
        return None


def jira_global_tag(task):
    """
    See jira_global_tag_v2. This function is only provided for backward compatibility.
    """

    result = jira_global_tag_v2(task)
    if result is None:
        return result

    if type(result) is tuple:  # ignore adjusted description
        result = result[0]
    if type(result) is str:    # use sub-issue instead of comment
        result = {
            "parent": {"key": result},
            "issuetype": {"id": "5"},
            }
    if "project" not in result.keys():
        result["project"] = {"key": "BII"}
    if "issuetype" not in result.keys():
        result["issuetype"] = {"name": "Task"}

    return result


def jira_global_tag_v2(task):
    """
    For a global tag update request, get the dictionary of the jira issue that will be created
    or a string with an issue key if a comment should be added to an existing issue.
    The dictionary can be empty. Then the default is to create an unassigned Task issue in the BII project.
    For creating a sub-issue the parent key has to be set and the isssuetype id has to be 5.
    The summary can be customized with a format string. Possible format keys are

    * tag: the upload GT name
    * user: the user name of the person who requests the GT update
    * reason: the reason for the update given by he user
    * release: the required release as specified by the user
    * request: the type of request: Addition, Update, or Change
    * task: the task = parameter of this function
    * time: the time stamp of the request

    A tuple can be used to customize the description. The first element is then the dictionary
    or string of the jira issue and the second element a format string for the description.
    The same fields as for the summary can be used for the description.

    The following examples show

    A) how to create a new jira issue in the BII project assigned to to user janedoe:

        return {"assignee": {"name": "janedoe"}}

    B) how to create a sub-issue (type id 5) of BII-12345 in the BII project
    assigned to user janedoe and a summary text containing the user name and time of the request::

        return {
            "project": {"key": "BII"},
            "parent": {"key": "BII-12345"},
            "issuetype": {"id": "5"},
            "assignee": {"name": "janedoe"},
            "summary": "Example global tag request by {user} at {time}"
            }

    C) how to add a comment to BII-12345::

        return "BII-12345"

    D) how to add a comment to BII-12345 with adjusted description containing only the global tag name
    and the reason for a request::

        return ("BII-12345", "Example comment for the global tag {tag} because of: {reason}")

    Parameters:
      task (str): An identifier of the task. Supported values are 'master', 'online', 'prompt', data', 'mc', 'analysis'

    Returns:
      The dictionary for the creation of a jira issue or a string for adding a comment to an
      existing issue or a tuple for an adjusted description or None if no jira issue should be created.
    """

    if task == 'master':
        return None
    elif task == 'online':
        return None
    elif task == 'prompt':
        return None
    elif task == 'data':
        return None
    elif task == 'mc':
        return None
    elif task == 'analysis':
        return None
