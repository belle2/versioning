#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Management of software versions and global tags.
"""

from distutils.version import LooseVersion
import json
import os
import tempfile
import shutil


# list of supported releases, the last one is the recommended one
_supported_releases = [
    'release-04-02-09',
    'release-05-01-16', 'release-05-02-00'
]

# list of supported light releases
_supported_light_releases = [
    'light-2012-minos', 'light-2102-nemesis', 'light-2103-oceanos'
]


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

    # update to latest supported light release
    if release.startswith('light-'):
        if release in _supported_light_releases:
            return release
        else:
            return _supported_light_releases[-1]

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
<li><a href="https://b2-master.belle2.org/development_build/index.html">Development Build</a></li>
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
    recommended = ' (recommended)'
    for supported in reversed(_supported_light_releases):
        table += ('<tr class="odd">\n<td><a href="sphinx/%s/index.html"><b>%s%s</b></a></td>\n<td><a href="%s/index.html"><b>%s</b></a></td>\n</tr>\n' % (supported, supported, recommended, supported, supported))
        recommended = ''
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

    metadata = None
    if not mc:
        metadata = [{'release': None}]

    result = recommended_global_tags_v2(release, input_tags, None, metadata)

    return result['tags']


def recommended_global_tags_v2(release, base_tags, user_tags, metadata):
    """
    Determine the recommended set of global tags for the given conditions.

    This function is called by b2conditionsdb-recommend and it may be called
    by conditions configuration callbacks. While it is in principle not limited
    to the use case of end user analysis this is expected to be the main case
    as in the other cases the production manager will most likely set the
    global tags explicitly in the steering file.

    Parameters:
      release (str): The release version that the user has set up.
      base_tags (list(str)): The global tags of the input files or default global tags in case of no input.
      user_tags (list(str)): The global tags provided by the user.
      metadata (list): The EventMetaData objects of the input files or None in case of no input.

    Returns:
      A dictionary with the following keys:
        tags   : list of recommended global tags (mandatory)
        message: a text message for the user (optional)
        release: a recommended release (optional)
    """

    # gather information that we may want to use for the decision about the recommended GT:
    # existing GTs, release used to create the input data
    existing_master_tags = [tag for tag in base_tags if tag.startswith('master_') or tag.startswith('release-')]
    existing_data_tags = [tag for tag in base_tags if tag.startswith('data_')]
    existing_mc_tags = [tag for tag in base_tags if tag.startswith('mc_')]
    existing_analysis_tags = [tag for tag in base_tags if tag.startswith('analysis_')]
    data_release = metadata[0]['release'] if metadata else None

    # if this is run-independent MC we dont want to show data tags (all other cases, we do)
    if metadata:
        is_mc = bool(metadata[0]['isMC'])
        experiments = [int(metadata[0]['experimentLow']), int(metadata[0]['experimentHigh'])]
        is_run_independent_mc = experiments[0] == experiments[1] and experiments[0] in [0, 1002, 1003]
    else:
        is_run_independent_mc = False


    # now construct the recommmendation
    result = {'tags': [], 'message': ''}

    # recommended release
    recommended_release = supported_release(release)
    if (release.startswith('release') or release.startswith('light')) and recommended_release != release:
        result['message'] += 'You are using %s, but we recommend to use %s.\n' % (release, recommended_release)
        result['release'] = recommended_release

    # tag to be used for (raw) data processing, depending on the release used for the processing
    # data_tags provides a mapping of supported release to the recommended data GT
    data_tags = {_supported_releases[-1]: 'data_reprocessing_proc9'}
    data_tag = data_tags.get(recommended_release, None)

    # tag to be used for run-dependent MC production, depending on the release used for the production
    # mc_tags provides a mapping of supported release to the recommended mc GT
    mc_tags = {_supported_releases[-1]: 'mc_production_mc12'}
    mc_tag = mc_tags.get(recommended_release, None)

    # tag to be used for analysis tools, depending on the release used for the analysis
    # analysis_tags provides a mapping of supported release to the recommended analysis GT
    analysis_tags = {_supported_releases[-1]: 'analysis_tools_light-2012-minos'}
    analysis_tag = analysis_tags.get(recommended_release, None)

    # In case of B2BII we do not have metadata
    if metadata == []:
        result['tags'] = ['B2BII']

    else:
        # If we have a master GT this means either we are generating events
        # or we read a file that was produced with it. So we keep it as last GT.
        result['tags'] += existing_master_tags

        # Always use online GT
        result['tags'].insert(0, 'online')

        # Prepend the data GT if the file is not run-independent MC
        if metadata is None or not is_run_independent_mc:
            if data_tag:
                result['tags'].insert(0, data_tag)
            else:
                result['message'] += 'WARNING: There is no recommended data global tag.'

        # Prepend the MC GT if we generate events (no metadata)
        # or if we read a file that was produced with a MC GT
        if metadata is None or existing_mc_tags:
            if mc_tag:
                result['tags'].insert(0, mc_tag)
            else:
                result['message'] += 'WARNING: There is no recommended mc global tag.'

    # Prepend the analysis GT
    if analysis_tag:
        result['tags'].insert(0, analysis_tag)
    else:
        result['message'] += 'WARNING: There is no recommended analysis global tag.'

    # What else do we want to tell the user?
    if result['tags'] != base_tags:
        result['message'] += 'The recommended tags differ from the base tags: %s' % ' '.join(base_tags) + '\n'
        result['message'] += 'Use the default conditions configuration if you want to take the base tags.\n'

    return result


def upload_global_tag(task):
    """
    Get the global tag that is supposed to be used for uploads for the given task.

    Parameters:
      task (str): An identifier of the task. Supported values are 'master', 'validation', 'online', 'prompt', data', 'mc', 'analysis'

    Returns:
      The name of the GT for uploads or None if a new GT should be created by the client for each upload request.
    """

    if task == 'master':
        return None
    elif task == 'validation':
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
      task (str): An identifier of the task. Supported values are 'master', 'validation', 'online', 'prompt', data', 'mc', 'analysis'

    Returns:
      The dictionary for the creation of a jira issue or a string for adding a comment to an
      existing issue or a tuple for an adjusted description or None if no jira issue should be created.
    """

    if task == 'master':
        return {"assignee": {"name": "ritter"}}
    elif task == 'validation':
        return {"assignee": {"name": "jikumar"}}
    elif task == 'online':
        return {"assignee": {"name": "seokhee"}}
    elif task == 'prompt':
        return {"assignee": {"name": "tamponi"}}
    elif task == 'data':
        return {"assignee": {"name": "tamponi"}}
    elif task == 'mc':
        return {"assignee": {"name": "jbennett"}}
    elif task == 'analysis':
        return {"assignee": {"name": "fmeier"}}


def create_jupyter_kernels(target_dir='~/.local/share/jupyter/kernels', top_dir='/cvmfs/belle.cern.ch'):
    """
    Create or update jupyter kernel files for the supported (light) releases

    Parameters:
      target_dir (str): The directory where the kernel files should be created.
      top_dir (str): The Belle II software top directory.
    """

    target_dir = os.path.expanduser(target_dir)
    top_dir = os.path.expanduser(top_dir)
    tools_dir = os.path.join(top_dir, "tools")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for release in _supported_releases + _supported_light_releases:
        name = release
        if name.startswith("release"):
            name = release.rsplit("-", 1)[0]  # remove patch version from name
        kernel_dir = os.path.join(target_dir, "belle2_" + name)
        if not os.path.exists(kernel_dir):
            os.mkdir(kernel_dir)
        if os.path.exists(os.path.join(tools_dir, "logo-64x64.png")):
            shutil.copy(os.path.join(tools_dir, "logo-64x64.png"), kernel_dir)
            shutil.copy(os.path.join(tools_dir, "logo-32x32.png"), kernel_dir)
        spec = {
            "display_name": "Belle2 (" + release + ")",
            "language": "python",
            "argv": [
                os.path.join(top_dir, "tools", "b2execute"), "-x", "python3",
                release, "-m", "ipykernel_launcher",
                "-f", "{connection_file}",
            ],
            "env": {
                "VO_BELLE2_SW_DIR": top_dir,
                "BELLE2_TOOLS": tools_dir
            }
        }
        with open(os.path.join(kernel_dir, "kernel.json"), "w") as specfile:
            json.dump(spec, specfile, indent=4)

        print("Created kernel for " + release)
