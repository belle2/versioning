#!/usr/bin/env python

"""
Management of software versions and global tags.
"""

from distutils.version import LooseVersion
import json
import os
import shutil

# recommended release
_recommended_release = 'light-2409-toyger'

# list of supported full releases
_supported_releases = [
    'release-05-01-25', 'release-05-02-19',
    'release-06-00-14', 'release-06-01-15', 'release-06-02-00',
    'release-08-00-10', 'release-08-01-10', 'release-08-02-02'
]

# list of supported light releases
_supported_light_releases = [
    'light-2401-ocicat', 'light-2403-persian', 'light-2405-quaxo', 'light-2406-ragdoll', 'light-2409-toyger'
]

assert _supported_releases == sorted(_supported_releases)
assert _supported_light_releases == sorted(_supported_light_releases)


def supported_release(release=None):
    """
    Check whether the given release is supported.

    Parameters:
      release (str): The release version to be checked.
       If release is None the recommended release version is returned.

    Returns:
      The name of the supported release that best matches the release given as input parameter.
    """

    # default is hard-coded release given above
    if release is None:
        return _recommended_release

    def basf2_version(release):
        return LooseVersion('.'.join(release.split('-')[1:]))

    # update to next supported release
    if release.startswith('pre'):
        release = release[3:19]

    if release == "release-":
        # Return the latest full release
        return _supported_releases[-1]
    elif release.startswith('release-'):
        # it is fine if a release newer than the latest supported one is used
        if basf2_version(release) >= basf2_version(_supported_releases[-1]):
            return release
        for supported in _supported_releases:
            if basf2_version(release) < basf2_version(supported):
                return supported

    # update to latest supported light release
    if release.startswith('light'):
        if release in _supported_light_releases:
            return release
        else:
            return _supported_light_releases[-1]

    # latest supported release
    return _supported_releases[-1]


def get_supported_releases(light=False):
    """Returns the list of recommended (light) releases"""

    if light:
        return reversed(_supported_light_releases)
    else:
        return reversed(_supported_releases)


def get_recommended_training_release():
    """Returns the recommended release for training purposes"""
    return supported_release("light")


def recommended_global_tags(release, mc=False, analysis=True, input_tags=None):
    """
    Determine the recommended set of global tags for the given conditions
    release, processing task, and tags used for the production of the input data.

    Parameters:
      release (str): The release version that the user has set up.
      mc (bool): Whether the MC GT should be added. Used for run-dependent MC.
      analysis (bool): Whether the analysis GT should be added. Used for skimming and analysis.
      input_tags (Optional(list)): The list of GTs used to produce the input file.

    Returns:
      The list of recommended GTs.
    """
    if input_tags is None:
        input_tags = []

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
    existing_main_tags = [tag for tag in base_tags if tag.startswith('main_') or tag.startswith(
        'master_') or tag.startswith('release-') or tag.startswith('prerelease-')]
    existing_data_tags = [tag for tag in base_tags if tag.startswith('data_')]
    existing_mc_tags = [tag for tag in base_tags if tag.startswith('mc_')]
    existing_analysis_tags = [tag for tag in base_tags if tag.startswith('analysis_')]
    data_release = metadata[0]['release'] if metadata else None

    # if this is run-independent MC we don't want to show data tags (all other cases, we do)
    if metadata:
        is_mc = bool(metadata[0]['isMC'])
        experiments = [int(metadata[0]['experimentLow']), int(metadata[0]['experimentHigh'])]
        is_run_independent_mc = experiments[0] == experiments[1] and experiments[0] in [0, 1002, 1003]
    else:
        is_run_independent_mc = False

    # now construct the recommendation
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
    _all_supported_releases = _supported_releases + _supported_light_releases + ['release-09-00-00']
    analysis_tags = dict(zip(_all_supported_releases, ['analysis_tools_light-2406-ragdoll'] * len(_all_supported_releases)))
    analysis_tag = analysis_tags.get(recommended_release, None)

    # In case of B2BII we do not have metadata
    if metadata == []:
        result['tags'] = ['B2BII']

    else:
        # If we have a main GT this means either we are generating events
        # or we read a file that was produced with it. So we keep it as last GT.
        result['tags'] += existing_main_tags

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


def recommended_b2bii_analysis_global_tag():
    """
    Get recommended global tag for B2BII analyses.
    """

    return 'analysis_b2bii'


def performance_recommendation_global_tag(campaign='MC15'):
    """
    Get global tag and payload name of the performance recommendation.
    """

    result = {'global_tag' : '',
              'payload' : 'recommendation_payload'}

    if campaign == 'MC15':
        result['global_tag'] = 'analysis_performance_recommendation_MC15'
    elif campaign == 'MC16':
        result['global_tag'] = 'analysis_performance_recommendation_MC16'

    return result


def upload_global_tag(task):
    """
    Get the global tag that is supposed to be used for uploads for the given task.

    Parameters:
      task (str): An identifier of the task. Supported values are 'master', 'main', 'validation', 'online', 'prompt', data', 'mc', 'analysis'

    Returns:
      The name of the GT for uploads or None if a new GT should be created by the client for each upload request.
    """

    if task == 'master':  # master is kept only for backward compatibility
        return None
    elif task == 'main':
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

    if isinstance(result, tuple):  # ignore adjusted description
        result = result[0]
    if isinstance(result, str):    # use sub-issue instead of comment
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
    TODO: provide an equivalent function for GitLab.

    For a global tag update request, get the dictionary of the jira issue that will be created
    or a string with an issue key if a comment should be added to an existing issue.
    The dictionary can be empty. Then the default is to create an unassigned Task issue in the BII project.
    For creating a sub-issue the parent key has to be set and the issuetype id has to be 5.
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

    A) how to create a new jira issue in the BII project assigned to user janedoe:

        return {"assignee": {"name": "janedoe"}}

    B) how to create a sub-issue (type id 5) of BII-12345 in the BII project
    assigned to user janedoe and a summary text containing the user name and time of the request:

        return {
            "project": {"key": "BII"},
            "parent": {"key": "BII-12345"},
            "issuetype": {"id": "5"},
            "assignee": {"name": "janedoe"},
            "summary": "Example global tag request by {user} at {time}"
            }

    C) how to add a comment to BII-12345:

        return "BII-12345"

    D) how to add a comment to BII-12345 with adjusted description containing only the global tag name
    and the reason for a request:

        return ("BII-12345", "Example comment for the global tag {tag} because of: {reason}")

    Parameters:
      task (str): An identifier of the task. Supported values are 'master', 'main', 'validation', 'online', 'prompt', data', 'mc', 'analysis'

    Returns:
      The dictionary for the creation of a jira issue or a string for adding a comment to an
      existing issue or a tuple for an adjusted description or None if no jira issue should be created.
    """

    if task == 'master':  # master is kept only for backward compatibility
        return {"assignee": {"name": "depietro"}}
    elif task == 'main':
        return {"assignee": {"name": "depietro"}}
    elif task == 'validation':
        return {"assignee": {"name": "jikumar"}}
    elif task == 'online':
        return {"assignee": {"name": "seokhee"}}
    elif task == 'prompt':
        return {"assignee": {"name": "mapr"}}
    elif task == 'data':
        return {"assignee": {"name": "mapr"}}
    elif task == 'mc':
        return {"assignee": {"name": "amartini"}}
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
            ]
        }
        with open(os.path.join(kernel_dir, "kernel.json"), "w") as specfile:
            json.dump(spec, specfile, indent=4)

        print("Created kernel for " + release)
