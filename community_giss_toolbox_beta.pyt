import os
import sys
import arcpy
import time
import shutil
import zipfile
import re
import subprocess
import json
import warnings
import fnmatch
import shlex
from glob import glob
from datetime import datetime, timedelta
import pandas as pd


class Toolbox(object):

    def __init__(self):
        self.label = 'Community GISS Tools - Beta'
        self.alias = 'CommunityGISSToolsBeta'

        # List of tool classes associated with this toolbox
        self.tools = [

        ]


class BaseBetaTool(object):
    """
    Base class to extend all
    """

    def __init__(self):
        self.label = 'Human-readble Label'
        self.description = '''
            This can be the same description from the class' doc string
        '''.replace('\n            ', ' ') # Do any additional post-processing on the string if you added other indentation


    def getParameterInfo(self):
        """
        This method is required by all Python Toolbox tools. It needs to return a list of parameters. Change the order
        here to rearrange the order of parameters in the tool dialog.
        """
        return []


    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True


    def execute(self):
        arcpy.AddWarning('This tool is provided to GISS users as part of the Beta toolbox from the Community GISS'
                         ' Tools. The results for any given ArcGIS Pro version are not guaranteed and you are using'
                         ' this tool at your own risk. For more information, see\n'
                         'https://github.com/smHooper/giss_community_tools')
        return



class ExampleTool(BaseBetaTool):
    """
    DESCRIPTION
    This tool reads the user's mind and does all the fancy whiz-bang things they've always dreamed of doing with fire
    incident data

    USAGE
    From the tool's dialog, the user specifies the incident root directory, envisions what they want to the tool to do,
    and this tool will take care of the rest


    REQUIREMENTS AND NOTES
    ArcGIS Pro 2.7+

    AUTHOR
    Sam Hooper, sam_hooper@firenet.gov
    """

    def __init__(self):
        self.label = 'Example Tool'
        self.description = '''
            This tool reads the user's mind and does all the fancy whiz-bang things they've always dreamed of doing with fire 
            incident data
        '''.replace('\n            ', ' ')

    def getParameterInfo(self):
        """
        This method is required by all Python Toolbox tools. It needs to return a list of parameters. Change the order
        here to rearrange the order of parameters in the tool dialog.
        """
        root_dir_path = arcpy.Parameter(
            displayName='''Specify the full path to an incident's root folder (like 2017_Boundary)''',
            name='root_dir_path',
            datatype='DEFolder',
            parameterType='Required',
            direction='Input'
        )
        
        return [
            root_dir_path
        ]


    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        return


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True


    def execute(self, parameters, messages):
        """

        """
        ##### Make sure to keep this call to the the BetaBaseTool class' execute() method #####
        super().execute()

        # ...your tool's execution code goes here... For instance:
        arcpy.AddMessage('Amazing things happening...')

