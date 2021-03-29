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


WINDOWS_MAX_PATH_LENGTH = 260


class Toolbox(object):

    def __init__(self):
        self.label = 'Community GISS Tools'
        self.alias = 'CommunityGISSTools'

        # List of tool classes associated with this toolbox
        self.tools = [
            CalculateGeometryAttributes,
            CalculateContainment,
            IncidentPeriodBackup,
            RoboCopyArchive
        ]


class CalculateGeometryAttributes(object):
    """
    DESCRIPTION
    This tool calculates LatWGS84_DDM, LongWGS84_DDM, LengthFeet, and GISAcres values in
    EventPoint, EventLine, EventPolygon, and AccountableProperty feature attribute tables
    where they are NULL, empty, of invalid format, or do not represent the feature's
    current geometry.

    USAGE
    Within the script tool's dialog, users must specify the current incident's:
    > Event geodatabase
    > Name
    > Projected spatial reference

    REQUIREMENTS AND NOTES
    > ArcMap 10.6+ or ArcPro 2.4+
    > An Event file or runtime geodatabase

    DISCLAIMER
    This script is made available for other's use on an "as is" basis, with no warranty,
    either expressed or implied, as to its fitness for any particular purpose.

    AUTHOR
    Carl Beyerhelm, Circle-5 GeoServices LLC, circle5geo@gmail.com, 928.607.3517
    Updated March, 2021 by Sam Hooper, sam_hooper@firenet.gov

    HISTORY
    13 Jul 2020 - Initial coding and testing
    14 Jul 2020 - Add code to clear any existing selections and definition queries on Event
                  layers, filter on incident name, and accept small attribute discrepancies
    10 Aug 2020 - Add code to test if input feature classes are referenced to GCS_WGS_1984
    09 Mar 2021 - Accept inputs with any CRS - Sam Hooper
    09 Mar 2021 - Optionally ignore interior rings for area calculations - Sam Hooper
    23 Mar 2021 - Migrate to Python toolbox
    """

    def __init__(self):
        self.label = 'Calculate Geometry Attributes'
        self.description = '''
            This tool calculates LatWGS84_DDM, LongWGS84_DDM, LengthFeet, and GISAcres values in EventPoint, EventLine,
            EventPolygon, and AccountableProperty feature attribute tables where they are NULL, empty, of invalid
            format, or do not represent the feature's existing geometry.
        '''.replace('\n            ', ' ')
        # For some reason, Python toolbox tools fail to run in Desktop unless self.canRunInBackground is False
        if not running_from_pro(warning=False):
            self.canRunInBackground = False

        # Code block for management.CalculateField() call
        #   This is ugly, but if the code block has indentation appropriate for the class, CalculateField() throws
        #   an error
        self.CODE_BLOCK_STR = """
import six

def get_wgs84_dd(geom):
    in_sr = geom.SpatialReference
    out_sr = arcpy.SpatialReference(4326)

    pt = arcpy.Point(geom.centroid.x, geom.centroid.y)
    wgs84_geom = arcpy.PointGeometry(pt, in_sr)\\
        .projectAs(out_sr)

    return wgs84_geom.centroid.Y, wgs84_geom.centroid.X


def dd_to_ddm(coord, is_lat=True):
    degree_symbol = u'\N{DEGREE SIGN}'
    if six.PY2:
        degree_symbol = degree_symbol.encode("iso-8859-1")
    deg = abs(int(coord))
    min = (abs(coord) - deg) * 60
    if coord > 0:
        dir = "N" if is_lat else "E"
    else:
        dir = "S" if is_lat else "W"

    return "{}{} {:06.3f}' {}".format(deg, degree_symbol, min, dir)


def geom_lat_as_ddm(geom):
    dd_lat, dd_lon = get_wgs84_dd(geom)
    return dd_to_ddm(dd_lat, is_lat=True)


def geom_lon_as_ddm(geom):
    dd_lat, dd_lon = get_wgs84_dd(geom)
    return dd_to_ddm(dd_lon, is_lat=False)
        """

    def getParameterInfo(self):
        """
        This method is required by all Python Toolbox tools. It needs to return a list of parameters. Change the order
        here to rearrange the order of parameters in the tool dialog.
        """
        event_geodatabase = arcpy.Parameter(
            displayName='''Specify the incident's Event geodatabase''',
            name='event_geodatabase',
            datatype='DEWorkspace',
            parameterType='Required',
            direction='Input'
        )

        incident_name = arcpy.Parameter(
            displayName='''Specify the incident's name''',
            name='incident_name',
            datatype='GPString',
            parameterType='Required',
            direction='Input'
        )

        spatial_reference = arcpy.Parameter(
            displayName='''Specify the incident's projected spatial reference''',
            name='spatial_reference',
            datatype='GPSpatialReference',
            parameterType='Required',
            direction='Input'
        )

        ignore_polygon_holes = arcpy.Parameter(
            displayName='Ignore interior holes when calculating polygon areas',
            name='ignore_polygon_holes',
            datatype='GPBoolean',
            parameterType='Optional',
            direction='Input'
        )
        
        return [
            event_geodatabase,
            incident_name,
            spatial_reference,
            ignore_polygon_holes
        ]

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # Set the spatial ref from the Event Polygon feature class (as long as it's projected)
        event_gdb = parameters[0].value#parameters[0].value
        workspace = arcpy.env.workspace

        if event_gdb:# and running_from_pro(warning=False):
            arcpy.env.workspace = event_gdb

            add_outputs = arcpy.env.addOutputsToMap # not sure if this is necessary, but get value so it can be reset
            arcpy.env.addOutputsToMap = False

            eventPolyName = arcpy.ListFeatureClasses("*Event*Polygon*")[0]
            lyr = arcpy.management.MakeFeatureLayer(eventPolyName, 'lyr')
            sr = arcpy.Describe(lyr).SpatialReference

            arcpy.env.addOutputsToMap = add_outputs

            if sr.type.lower() != "geographic":
                parameters[2].value = sr
            if arcpy.Exists('lyr'):
                arcpy.management.Delete('lyr')

            arcpy.env.workspace = workspace

        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        # Verify that params[0] includes IncidentName values.

        #workspace = arcpy.env.workspace

        if parameters[0].value:  ## If params[0] has a value
            arcpy.env.workspace = parameters[0].value  ## Set the workspace to the specified GDB
            eventPoly = arcpy.ListFeatureClasses('*Event*Polygon*')[0]  ## Set eventPoly
            incidentList = []  ## Initialize an empty list of incident names
            with arcpy.da.SearchCursor(eventPoly, 'IncidentName') as rows:  ## Search eventPoly to build a list of incident names
                for row in rows:
                    name = row[0]
                    # Append unique, non-NULL, non-space values of IncidentName to the list
                    if name and not name.isspace() and name not in incidentList:
                        incidentList.append(name)

            # Set the incident_name filter list
            if incidentList:
                parameters[0].clearMessage()
                parameters[1].filter.list = sorted(incidentList)
            else:
                parameters[1].filter.list = incidentList  ## Use incidentList as a value list for params[1]
                parameters[1].value = ""  ## Set the value of params[1] to blank
                parameters[0].setErrorMessage("The specified Event Polygon feature class contains no incident names.")

        # Verify that params[2] is a PROJECTED spatial reference.
        if parameters[2].value:
            if parameters[2].value.type == "Geographic":
                parameters[2].setErrorMessage("Please specify a PROJECTED spatial reference.")
            else:
                parameters[2].clearMessage()  ## Clear any existing message for params[2]

        return

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def calculate_geometry_attributes(self, event_gdb_path=None, incident_name=None, event_spatial_ref=None, ignore_polygon_holes=False):
        """
        Helper function to be able to call script from either Toolbox dialog or command line with other arguments

        :param event_gdb_path: string path to geodatabase
        :param incident_name: string incident name found in Event_Polygon to select only incident features
        :param event_srs_epsg: EPSG code for the event spatial reference system
        :param ignore_polygon_holes: boolean indicating whether to ignore polygon holes in
        :return:
        """

        start_time = time.time()

        arcpy.AddMessage("\n\nCalculate Geometry Attributes was developed by Carl Beyerhelm, Circle-5 GeoServices LLC.\n")

        try:
            # Test if running from the command line
            is_cli = running_from_cli()

            # Check if running from the arcpro Python executable
            is_arcpro = running_from_pro()

            if is_cli:
                # Since this is running from the command line, get the spatial reference from the specified EPSG code
                event_spatial_ref = arcpy.SpatialReference(int(event_spatial_ref))

            else:
                # Clear any active selections or definition queries on Event layers.
                if is_arcpro:
                    proDoc = arcpy.mp.ArcGISProject('current')  ## Get the current APRX
                    mapList = proDoc.listMaps()  ## Get a list of the APRX's maps
                    for map in mapList:  ## For each map
                        map.clearSelection()  ## Clear any selections in the map
                        lyrList = map.listLayers()  ## Get a list of the map's layers
                        for lyr in lyrList:  ## For each layer
                            if lyr.supports("DEFINITIONQUERY"):  ## If the layer supports definition queries
                                lyr.definitionQuery = None  ## Clear any definition queries in the layer
                    del proDoc
                else:  ## ArcMap session
                    mapDoc = arcpy.mapping.MapDocument('current')
                    for lyr in arcpy.mapping.ListLayers(mapDoc):
                        if lyr.isFeatureLayer:
                            lyr.definitionQuery = None
                            arcpy.SelectLayerByAttribute_management(lyr, "CLEAR_SELECTION")
                    del mapDoc

            arcpy.env.workspace = event_gdb_path
            arcpy.env.addOutputsToMap = False  ## Prevent geoprocessing results from appearing in the data/map frame
            arcpy.env.overwriteOutput = True  ## Permit overwriting of temporary feature layers and in_memory layers
            arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"  ## Set the default WGS84/NAD83 transformation
            eventPointName = arcpy.ListFeatureClasses("*Event*Point*")[0]  ## The incident EventPoint feature class
            eventLineName = arcpy.ListFeatureClasses("*Event*Line*")[0]  ## The incident EventLine feature class
            eventPolygonName = arcpy.ListFeatureClasses("*Event*Polygon*")[0]  ## The incident EventPolygon feature class
            eventPropertyName = arcpy.ListFeatureClasses("*Accountable*Property*")[0]  ## the incident AccountableProperty feature class

            # Create xxDirtyAtts from pointFCName's potentially dirty LatWGS84_DDM and LongWGS84_DDM attributes.
            #   Determine which records have invalid lat/lons by trying to create points from the
            #   LatWGS84_DDM and LongWGS84_DDM fields. Any features whose geometry from text doesn't
            #   match the original geometry should be updated
            incident_name_filter = "IncidentName = '%s'" % incident_name
            with arcpy.da.Editor(event_gdb_path) as edit:
                for pointFCName in (eventPointName, eventPropertyName):
                    xxDirtyLYR = arcpy.MakeFeatureLayer_management(pointFCName, "xxDirtyLYR",
                                                                   incident_name_filter)  ## Filter the feature layer on incident_name
                    arcpy.ConvertCoordinateNotation_management("xxDirtyLYR", "in_memory\\xxDirtyAtts", "LongWGS84_DDM", "LatWGS84_DDM", "DDM_2", "DD_NUMERIC")

                    # Copy xxDirtyLYR to xxClean, and calc all its geometry attributes to reflect each feature's current ("clean") geometry.
                    arcpy.CopyFeatures_management("xxDirtyLYR", "in_memory\\xxClean")
                    arcpy.CalculateField_management("in_memory\\xxClean", "LatWGS84_DDM", "geom_lat_as_ddm(!SHAPE!)", "PYTHON_9.3", self.CODE_BLOCK_STR)
                    arcpy.CalculateField_management("in_memory\\xxClean", "LongWGS84_DDM", "geom_lon_as_ddm(!SHAPE!)", "PYTHON_9.3", self.CODE_BLOCK_STR)

                    # Create xxCleanAtts from xxClean's clean LatWGS84_DDM and LongWGS84_DDM attributes.
                    arcpy.ConvertCoordinateNotation_management("in_memory\\xxClean", "in_memory\\xxCleanAtts", "LongWGS84_DDM", "LatWGS84_DDM", "DDM_2", "DD_NUMERIC")

                    # Select xxDirtyAtts features that are identical to xxCleanAtts features by location.  These feature's geometry attributes match their current geometry.
                    # Then, use SWITCH_SELECTION to identify the xxdirtyAtts features whose geometry attributes don't match their current geometry.
                    arcpy.MakeFeatureLayer_management("in_memory\\xxDirtyAtts", "xxDirtyAttsLYR")  ## Make a feature layer from xxDirtyAtts
                    arcpy.SelectLayerByLocation_management("xxDirtyAttsLYR", "ARE_IDENTICAL_TO", "in_memory\\xxCleanAtts")
                    arcpy.SelectLayerByAttribute_management("xxDirtyAttsLYR", "SWITCH_SELECTION")  ## Identifies the dirty (non-matching) features in xxDirtyAttsLYR
                    count = str(arcpy.GetCount_management("xxDirtyAttsLYR"))

                    # Make a list of the original parent OBJECTID values from the selected dirty features in xxDirtyAtts.
                    # oidList = ""
                    with arcpy.da.SearchCursor("xxDirtyAttsLYR", ["ORIG_OID"]) as rows:
                        oid_string = ','.join([str(row[0]) for row in rows])
                    arcpy.SelectLayerByAttribute_management("xxDirtyAttsLYR", "CLEAR_SELECTION")

                    # Select pointFCName features that match the OBJECTIDs in oidList.  These are the pointFCName features with dirty geometry attributes.
                    # Then, calc each selected feature's geometry attributes to reflect the feature's current geometry.
                    if count != '0':
                        # arcpy.MakeFeatureLayer_management(pointFCName, "xxDirtyLYR")#, "OBJECTID in (%s)" % oid_string)  ## Filter feature layer on oidList (the list of dirty features)
                        arcpy.CalculateField_management("xxDirtyLYR", "LatWGS84_DDM", "geom_lat_as_ddm(!SHAPE!)", "PYTHON_9.3", self.CODE_BLOCK_STR)
                        arcpy.CalculateField_management("xxDirtyLYR", "LongWGS84_DDM", "geom_lon_as_ddm(!SHAPE!)",  "PYTHON_9.3", self.CODE_BLOCK_STR)
                    arcpy.AddMessage("\nLatWGS84_DDM and LongWGS84_DDM attributes were calculated for %s %s features." % (count, pointFCName))

            # Use an UpdateCursor to discover and update eventLine feature attributes where LengthFeet does not match SHAPE@ length rounded to the nearest foot.
            count = 0
            with arcpy.da.UpdateCursor(eventLineName, ["SHAPE@", "LengthFeet", "IncidentName"],
                                       incident_name_filter) as cursor:  ## Filter cursor on incident_name
                for row in cursor:
                    calculated_length = int(round(row[0].projectAs(event_spatial_ref).getLength("PLANAR", "FEET")))
                    if calculated_length != row[1]:  ## Must match to the rounded whole foot
                        row[1] = calculated_length
                        cursor.updateRow(row)
                        count += 1

            arcpy.AddMessage("\nLengthFeet attributes were calculated for %s %s features." % (count, eventLineName))

            # Use an UpdateCursor to discover and update eventPolygon feature attributes where GISAcres does not match SHAPE@ area exactly.
            count = 0
            with arcpy.da.UpdateCursor(eventPolygonName, ["SHAPE@", "GISAcres", "IncidentName"],
                                       incident_name_filter) as cursor:  ## Filter cursor on incident_name
                for row in cursor:
                    geometry = row[0]

                    # If the user specified the option to ignore interior rings, try to remove them in the geometry
                    if ignore_polygon_holes:
                        # Collect outer parts of the geometry in an Array
                        outer_geom_parts = arcpy.Array()

                        # Verticies in a geometry part object are == None if they're verticies of an interior ring
                        # Loop through each part of the (potentially) multi-part geometry and check for inner rings
                        for part in geometry:
                            # Initialize the
                            first_null_point_index = 0

                            # Loop through each vertex and check if it's null
                            for i in range(len(part)):
                                if part[i] == None:
                                    first_null_point_index = i
                                    break
                            # If there were no null verticies (i.e., no interior rings), first_null_point_index will
                            #   still be 0. In that case, keep the whole part
                            if first_null_point_index == 0:
                                outer_geom_parts.add(part)
                            # Otherwise, keep all vertices up to the first null one found
                            else:
                                new_part = arcpy.Array()
                                for i in range(first_null_point_index):
                                    new_part.add(part[i])

                                outer_geom_parts.add(new_part)

                        # If the new geometry is valid, replace the geometry object with the cleaned outer geometry
                        if len(outer_geom_parts) > 0:
                            geometry = arcpy.Polygon(outer_geom_parts)

                    calculated_area = geometry.projectAs(event_spatial_ref).getArea("PLANAR", "ACRES")
                    if calculated_area != row[1]:  ## Must match exactly
                        row[1] = calculated_area
                        cursor.updateRow(row)
                        count += 1

            arcpy.AddMessage("\nGISAcres attributes were calculated for %s %s features.\n\n" % (count, eventPolygonName))
            arcpy.AddMessage("\n\nCalculate Geometry Attributes finished in %s\n" % format_elapsed_seconds(time.time() - start_time))

        except SystemExit:
            pass
        except:
            error = arcpy.GetMessages(2)
            arcpy.AddMessage("%s" % (error))

        finally:
            # Clean up.
            if arcpy.Exists("in_memory\\xxDirtyAtts"):
                arcpy.Delete_management("in_memory\\xxDirtyAtts")
            if arcpy.Exists("in_memory\\xxClean"):
                arcpy.Delete_management("in_memory\\xxClean")
            if arcpy.Exists("in_memory\\xxCleanAtts"):
                arcpy.Delete_management("in_memory\\xxCleanAtts")
            if arcpy.Exists("xxDirtyAttsLYR"):
                arcpy.Delete_management("xxDirtyAttsLYR")

    def execute(self, parameters, messages):
        return self.calculate_geometry_attributes(
            parameters[0].valueAsText, # event_gdb
            parameters[1].valueAsText, # incident_name
            parameters[2].value,       # event spatial ref
            parameters[3].value        # include holes flag
        ) # returns nothing, but that might change in the future


class CalculateContainment(object):
    """
    DESCRIPTION:
    This script tool calculates the percent of containment as:
    > The summed projected length of a fire's exterior perimeter(s)
    > Minus the summed projected length of a fire's exterior Uncontrolled Fire Edge line(s)
    > Divided by the summed projected length of a fire's exterior perimeter(s)
    > Multiplied by 100

    REQUIREMENTS:
    > ArcMap 10.x or ArcPro 2.x
    > An Event geodatabase (file or runtime) containing Wildfire Daily Fire Perimeter
      polygons and Uncontrolled Fire Edge lines
    > Attribution of IncidentName and FeatureCategory fields that is complete and correct

    DISCLAIMER:
    This script is made available for other's use on an "as is" basis, with no warranty,
    either expressed or implied, as to its fitness for any particular purpose.

    AUTHOR:
    Carl Beyerhelm, Circle-5 GeoServices LLC, circle5geo@gmail.com, 928.607.3517
    Updated March, 2021 by Sam Hooper, sam_hooper@firenet.gov

    HISTORY:
    25 Feb 2018 - Develop initial code, and test
    17 Mar 2018 - Revise code to accommodate BASIC licensing by using a UNION method instead
                  of the original EliminatePolygonPart method
    07 Aug 2019 - Convert the widget from Add-In to Toolbox format
    07 Aug 2019 - Add code to restrict processing to only the features that match a
                  user-supplied incident name
    25 Jun 2020 - Revise code to accommodate various spellings of EventPolygon and
                  EventLine
    25 Jun 2020 - Add code to convert multi-part features to single-part
    18 Mar 2021 - Make SQL expression for selecting fire edge compatible with 2021 NIFS category "Fire Edge" - Sam Hooper
    18 Mar 2021 - Write all intermediate geoprocessing results to in_memory workspace - Sam Hooper
    18 Mar 2021 - Changed fatal errors from "arcpy.AddWarning(); sys.eixt()" to "arcpy.AddError(); sys.exit()"
    22 Mar 2021 - Migrate to Python toolbox
    """

    def __init__(self):
        self.label = 'Calculate Containment'
        self.description = '''This script tool calculates the percent of GIS containment as:
            > The summed projected length of a fire's exterior perimeter(s)
            > Minus the summed projected length of a fire's exterior Uncontrolled Fire Edge line(s)
            > Divided by the summed projected length of a fire's exterior perimeter(s)
            > Multiplied by 100
            
            Note that the containment calculation is printed to the messages window of the tool's dialog. Click 
            'View Details' and expand 'Messages' once the tool has finished running to see the calculation result.
        '''.replace('\n            ', '\n   ')
        # For some reason, Python toolbox tools fail to run in Desktop unless self.canRunInBackground is False
        if not running_from_pro(warning=False):
            self.canRunInBackground = False

    def getParameterInfo(self):
        """
        This method is required by all Python Toolbox tools. It needs to return a list of parameters. Change the order
        here to rearrange the order of parameters in the tool dialog.
        """
        event_polygon = arcpy.Parameter(
            displayName='''Specify the current incident's EventPolygon feature class:''',
            name='event_polygon',
            datatype='GPFeatureLayer',
            parameterType='Required',
            direction='Input'
        )
        event_polygon.filter.list = ["Polygon"]

        incident_name = arcpy.Parameter(
            displayName='''Specify the current incident's name:''',
            name='incident_name',
            datatype='GPString',
            parameterType='Required',
            direction='Input'
        )

        spatial_reference = arcpy.Parameter(
            displayName='''Specify the incident's projected spatial reference''',
            name='spatial_reference',
            datatype='GPSpatialReference',
            parameterType='Required',
            direction='Input'
        )

        return [
            event_polygon,
            incident_name,
            spatial_reference
        ]

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # Set the spatial ref from the Event Polygon feature class (as long as it's projected)
        event_polygon_param, incident_name_param, event_spatial_reference_param = parameters

        if event_polygon_param.value and not event_polygon_param.hasBeenValidated:  # and running_from_pro(warning=False):
            add_outputs = arcpy.env.addOutputsToMap  # not sure if this is necessary, but get value so it can be reset
            arcpy.env.addOutputsToMap = False

            lyr = arcpy.management.MakeFeatureLayer(event_polygon_param.value, 'lyr')
            sr = arcpy.Describe(lyr).SpatialReference

            arcpy.env.addOutputsToMap = add_outputs

            if sr.type.lower() == 'projected':
                event_spatial_reference_param.value = sr
            if arcpy.Exists('lyr'):
                arcpy.management.Delete('lyr')

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        event_polygon_param, incident_name_param, spatrial_ref_param = parameters

        if event_polygon_param.value:
            incidentList = []  ## Initialize an empty list of incident names
            with arcpy.da.SearchCursor(event_polygon_param.value, 'IncidentName') as rows:  ## Search eventPoly to build a list of incident names
                for row in rows:
                    name = row[0]
                    # Append unique, non-NULL, non-space values of IncidentName to the list
                    if name and not name.isspace() and name not in incidentList:
                        incidentList.append(name)

            # Set the incident_name filter list
            if incidentList:
                event_polygon_param.clearMessage()
                incident_name_param.filter.list = sorted(incidentList)
            else:
                incident_name_param.filter.list = incidentList  ## Use incidentList as a value list for params[1]
                incident_name_param.value = ""  ## Set the value of params[1] to blank
                event_polygon_param.setErrorMessage("The specified Event Polygon feature class does not contain any incident names.")

        # Verify that params[2] is a PROJECTED spatial reference.
        if spatrial_ref_param.value:
            if spatrial_ref_param.value.type.lower() != "projected":
                spatrial_ref_param.setErrorMessage("You must specify a PROJECTED spatial reference.")
            else:
                spatrial_ref_param.clearMessage()  ## Clear any existing message for params[2]'

        return

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def calculate_containment(self, event_polygon_path=None, incident_name=None, event_spatial_ref=None):
        """
        Helper function to be able to call script from either Toolbox dialog or command line with other arguments

        :param event_gdb_path: string path to geodatabase
        :param incident_name: string incident name found in Event_Polygon to select only incident features
        :param event_srs_epsg: EPSG code for the event spatial reference system
        :param ignore_polygon_holes: boolean indicating whether to ignore polygon holes in
        :return:
        """

        try:
            arcpy.AddMessage(
                "\n\n" + "Calc GIS Containment was developed by Carl Beyerhelm, Circle-5 GeoServices LLC" + "\n\n")

            # Check if use is running tool from ArcMap. If so, issue deprecation warning
            is_arcpro = running_from_pro()

            # Initialize variables and environments.
            if running_from_cli():
                event_spatial_ref = arcpy.SpatialReference(int(event_spatial_ref))#numeric epsg code

            arcpy.env.workspace = os.path.dirname(event_polygon_path)  ## Set workspace to the Event GDB
            arcpy.env.addOutputsToMap = False  ## Prevent geoprocessing results from flashing on-screen

            #### Make a feature layer of the incident's Wildfire Daily Fire Perimeter polygons.
            incident_name_expression = '''AND IncidentName = '%s' ''' % incident_name
            arcpy.MakeFeatureLayer_management(event_polygon_path, r"in_memory\polyLyr", "FeatureCategory = 'Wildfire Daily Fire Perimeter' " + incident_name_expression)
            if int(arcpy.GetCount_management(r"in_memory\polyLyr").getOutput(0)) == 0:
                arcpy.AddError(
                    "The Event Polygon feature class given does not contain any Wildfire Daily Fire Perimeter polygons "
                    "with an Incident Name of '{}'.\n\n".format(incident_name)
                )
                sys.exit()

            #### Remove voids from event_polygon_path.
            # Get an in-memory layer with all voids filled in as polygon features
            #   The NO_GAPS option fills polygon voids
            arcpy.Union_analysis(r"in_memory\polyLyr", r"in_memory\prepPoly", "ONLY_FID", "#", "NO_GAPS")

            # Set all FID_EventPolygon (field created by Union()) values to 0
            # .split()[-1] returns the post-period portion of event_polygon in a runtime GDB
            event_polygon_fc_name = os.path.basename(event_polygon_path).split(".")[-1]
            fidField = "FID_" + event_polygon_fc_name
            arcpy.CalculateField_management(r"in_memory\prepPoly", fidField, 0)

            # Dissolve to single-parts on FID_EventPolygon
            arcpy.Dissolve_management(r"in_memory\prepPoly", r"in_memory\noVoidPoly", fidField, "#", "SINGLE_PART")
            arcpy.management.Delete(r"in_memory\polyLyr")
            arcpy.management.Delete(r"in_memory\prepPoly")

            # Define function for cumulative length because the code is identical for polygons and lines
            def get_cumulative_length(layer_name, feature_spatial_ref):
                length = 0  ## The summed exterior projected length of Wildfire Daily Fire Perimeter polygons
                with arcpy.da.SearchCursor(layer_name, ["SHAPE@"]) as cursor:
                    for row in cursor:
                        if feature_spatial_ref != event_spatial_ref:
                            geometry = row[0].projectAs(event_spatial_ref)  # Project geometry using specified event spatial ref
                        else:
                            geometry = row[0]  # Spatial refs match so no projection is required
                        length += geometry.getLength("PLANAR", "FEET")
                return length

            #### Sum projected lengths of the exterior fire perimeter no-void polygons.
            event_polygon_sr = arcpy.Describe(event_polygon_path).spatialReference
            extPolyLength = get_cumulative_length(r"in_memory\noVoidPoly", event_polygon_sr)  ## The summed exterior projected length of Wildfire Daily Fire Perimeter polygons

            # Get the EventLine feature class, and make it single-part.
            eventLine = arcpy.ListFeatureClasses("*Event*Line*")[0]
            arcpy.MultipartToSinglepart_management(eventLine, r"in_memory\lineLyr0")

            # Make a feature layer of the incident's Uncontrolled Fire Edge lines that are not "COMPLETELY WITHIN" the no-void polygons.
            arcpy.MakeFeatureLayer_management(r"in_memory\lineLyr0", r"in_memory\lineLyr1", "FeatureCategory LIKE '%Fire Edge' " + incident_name_expression)
            # Select all of the feature layer's features
            arcpy.SelectLayerByAttribute_management(r"in_memory\lineLyr1", "NEW_SELECTION")
            # Remove interior features
            arcpy.SelectLayerByLocation_management(r"in_memory\lineLyr1", "COMPLETELY_WITHIN", r"in_memory\noVoidPoly", 0, "REMOVE_FROM_SELECTION")

            # Sum projected lengths of the exterior uncontrolled fire edge lines.
            event_line_sr = arcpy.Describe(event_polygon_path).spatialReference
            extLineLength = get_cumulative_length("in_memory\lineLyr1", event_line_sr)

            arcpy.SelectLayerByAttribute_management(r"in_memory\lineLyr1", "CLEAR_SELECTION")
            arcpy.management.Delete(r"in_memory\lineLyr0")
            arcpy.management.Delete(r"in_memory\lineLyr1")
            arcpy.management.Delete(r"in_memory\noVoidPoly")

            # Calculate containment.
            containPercent = (extPolyLength - extLineLength) / extPolyLength * 100

            # Issue success message.
            arcpy.AddMessage(
                "Specified incident name: {}\n".format(incident_name) +
                "Specified projected spatial reference: \n".format(event_spatial_ref.name) +
                "Exterior fire perimeter length (feet): {:,.0f}\n".format(extPolyLength)  +
                "Exterior uncontrolled fire edge length (feet): {:,.0f}\n\n".format(extLineLength) +
                "Percent GIS containment = {:.1f}% \n\n".format(containPercent)
            )

        except SystemExit:
            pass
        except:
            error = arcpy.GetMessages(2)
            arcpy.AddError(error)

        finally:
            # Final clean up.
            if arcpy.Exists(r"in_memory\polyLyr"):
                arcpy.Delete_management(r"in_memory\polyLyr")
            if arcpy.Exists(r"in_memory\lineLyr1"):
                arcpy.Delete_management(r"in_memory\lineLyr1")
            if arcpy.Exists(r"in_memory\prepPoly"):
                arcpy.Delete_management(r"in_memory\prepPoly")
            if arcpy.Exists(r"in_memory\noVoidPoly"):
                arcpy.Delete_management(r"in_memory\noVoidPoly")
            if arcpy.Exists(r"in_memory\lineLyr0"):
                arcpy.Delete_management(r"in_memory\lineLyr0")
            arcpy.env.addOutputsToMap = True
            if not is_arcpro:
                arcpy.RefreshActiveView()

    def execute(self, parameters, messages):

        return self.calculate_containment(
            event_polygon_path=parameters[0].valueAsText,
            incident_name=parameters[1].valueAsText,
            event_spatial_ref=parameters[2].value
        )  # returns nothing, but that might change in the future


class IncidentPeriodBackup(object):
    """
    DESCRIPTION:
    This tool will compact, back up, and zip all MDB and GDB geodatabases in the
    INCIDENT_DATA folder, and back up all MXD and APRX files in the PROJECTS folder, to
    their respective dated backup folders using GSTOP-compliant names, where possible.

    REQUIREMENTS:
    > ArcMap 10.x or ArcPro 2.x
    > Incident folder structure and folder/file names must match GeoOps conventions.

    USER INPUTS:
    > User specifies the incident's root folder, like 2017_Boundary.
    > User specifies a yyyymmdd date stamp for the dated backup folders, like 20170630.
    > Optionally, user specifies whether or not to back up MXD and APRX project files.
    > Optionally, user specifies whether or not to zip geodatabase backups.

    FUNCTIONALITY:
    > Checks if the INCIDENT_DATA folder exists.
    > Checks if the PROJECTS folder exists.
    > Checks if a BACKUPS folder exists under the INCIDENT_DATA folder, and under the
      PROJECTS folder, and creates a BACKUPS folder if one isn't found.
    > Checks if the user-specified dated data backup folder exists, and creates one if
      that folder isn't found.
    > Checks if the user-specified dated project backup folder exists, and creates one if
      that folder isn't found.
    > Creates a list of all MDBs and GDBs in the INCIDENT_DATA folder.
    > Compacts each geodatabase.
    > Backs up each geodatabase to the user-specified dated data backup folder
      according to the GSTOP file naming convention, where possible.
    > Optionally, zips each geodatabase backup.
    > Optionally, creates a list of all MXD and APRX projects in the PROJECTS folder.
    > Optionally, backs up each MXD and APRX to the user-specified dated project backup
      folder according to the GSTOP file naming convention, where possible.

    DISCLAIMER:
    This script is made available for other's use on an "as is" basis, with no warranty,
    either expressed or implied, as to its fitness for any particular purpose.

    AUTHOR:
    Carl Beyerhelm - Circle-5 GeoServices LLC, circle5geo@gmail.com, 928.607.3517
    Updated March, 2021 by Sam Hooper, sam_hooper@firenet.gov

    HISTORY:
    30 Jun 2011 - Complete original coding and testing
    12 Jul 2011 - Add option to skip project file back up
    19 Aug 2012 - Adapt to ArcGIS 10x using ArcPy, and to the 2012 GSTOP conventions
    12 Apr 2014 - Revise to accommodate the 2014 GSTOP conventions
    27 Jun 2015 - Revise to expand schema lock testing from only the feature datasets to
                  include stand-alone feature classes and stand-alone tables
    12 Sep 2017 - Rename the script and toolbox, and remove references to FIMT
    05 Dec 2017 - Consolidate code and test various workflows
    11 Dec 2017 - Add option to zip geodatabase backups
    28 Jun 2019 - Drop schema lock test, substitute shutil.copy for arcpy.Copy_management,
                  expand processing to all geodatabases and MXDs, consolidate code, and
                  test various workflows
    12 Apr 2020 - Revise code to have shutil.copytree ignore files with a *.lock extension
    12 Apr 2020 - Add code to include APRX files during project back up to work with ArcPro
    11 Mar 2020 - Wrap in main() function and store and resuse results of duplicated code - Sam Hooper
    11 Mar 2020 - Make helper functions for backing up GDBs to reduce duplicated code - Sam Hooper
    11 Mar 2020 - Don't try to compress non-.gdb files because ArcPro crashes - Sam Hooper
    11 Mar 2020 - Remove outer try/except block because it only obscures errors but doesn't offer any benefit
    22 Mar 2021 - Migrate to Python toolbox
    """

    def __init__(self):
        self.label = 'Incident Period Backup'
        self.description = '''
            This tool will compact, back up, and zip all MDB and GDB geodatabases in the 
            INCIDENT_DATA folder, and back up all MXD and APRX files in the PROJECTS folder, to 
            their respective dated backup folders using GSTOP-compliant names, where possible.
        '''.replace('\n            ', ' ')
        # For some reason, Python toolbox tools fail to run in Desktop unless self.canRunInBackground is False
        if not running_from_pro(warning=False):
            self.canRunInBackground = False

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
        incident_root_dir = find_incident_root_parent_dir()
        if incident_root_dir:
            root_dir_path.value = incident_root_dir

        datestamp = arcpy.Parameter(
            displayName='''Specify a GeoOps-complaint date stamp for the backup folder (like 20170630)''',
            name='datestamp',
            datatype='GPString',
            parameterType='Required',
            direction='Input'
        )
        datestamp.value = time.strftime('%Y%m%d')

        backup_projects = arcpy.Parameter(
            displayName='Backup MXD and APRX files this session',
            name='backup_projects',
            datatype='GPBoolean',
            parameterType='Required',
            direction='Input'
        )
        backup_projects.value = True

        zip_gdbs = arcpy.Parameter(
            displayName='Zip geodatabase backups this session',
            name='zip_gdbs',
            datatype='GPBoolean',
            parameterType='Required',
            direction='Input'
        )
        zip_gdbs.value = True

        return [
            root_dir_path,
            datestamp,
            backup_projects,
            zip_gdbs
        ]

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        #root_dir_path, date_stamp, backup_projects, zip_gdbs = parameters

        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # Check that the specified incident directory exists
        root_dir_path, datestamp, backup_projects, zip_gdbs = parameters
        if not os.path.isdir(root_dir_path.valueAsText):
            root_dir_path.setErrorMessage('The specified path does not exist or is not a directory')
        else:
            root_dir_path.clearMessage()

        # Verify that the datestamp param is in YYYYMMDD format
        try:
            datetime.strptime(datestamp.value, '%Y%m%d')
            datestamp.clearMessage()
        except:
            datestamp.setErrorMessage('The date stamp must be in the format YYYYMMDD')

        return


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True


    def incident_period_backup(self, root_folder=None, datestamp=None, backup_projects=True, zip_gdbs=True):
        """
        Helper function to be able to call script from either Toolbox dialog or command line with other arguments
        """

        start_time = time.time()

        is_cli = running_from_cli()
        running_from_pro()  # Call this for the warning to ArcGIS Desktop users

        # Accept user inputs.
        if is_cli:
            # Booleans will be read as text from the command line so convert to actual bool
            backup_projects = str(backup_projects).lower() == 'true'
            zip_gdbs = str(zip_gdbs).lower() == 'true'

        # Establish variables.
        backup_timestamp = time.strftime('%Y%m%d_%H%M')
        incident_data_dir = os.path.join(root_folder, "incident_data")
        incident_backups_dir = os.path.join(incident_data_dir, "backups", datestamp)

        root_folder_basename = os.path.basename(root_folder)

        arcpy.AddMessage("\n\nIncident Periodic Back Up was developed by Carl Beyerhelm, Circle-5 GeoServices LLC\n")

        # Test for existence of the INCIDENT_DATA folder, the BACKUPS folder, and the dated data backup folder.
        if os.path.isdir(incident_data_dir):
            if not os.path.isdir(incident_backups_dir):
                os.makedirs(incident_backups_dir)  ## Create the BACKUPS folder
                arcpy.AddMessage("\nCreated folder " + incident_backups_dir)

            # Identify, compact, back up, and zip geodatabases from the INCIDENT_DATA folder.
            arcpy.env.workspace = incident_data_dir
            gdb_list = arcpy.ListWorkspaces("*.*db")  ## Get a list (full path and filename) of GDB and MDB geodatabases
            if len(gdb_list) > 0:
                arcpy.AddMessage("\nProcessing geodatabases...")

                # Define helper functions for backing up GDBs to reduce code duplication
                def backup_fgdb(gdb_path, backup_path, zip_gdbs):
                    """
                    Helper function to backup a file geodatbase
                    """
                    ## Copy_management() broke at 10.5.1 so use shutit
                    shutil.copytree(gdb_path, backup_path, ignore=shutil.ignore_patterns("*.lock"))
                    arcpy.AddMessage("\t\tBacked up...")
                    backup_dir, backup_name = os.path.split(backup_path)
                    if zip_gdbs:
                        shutil.make_archive(backup_path, "zip", backup_dir, backup_name)
                        arcpy.AddMessage("\t\tZipped...")

                def backup_mdb(gdb_path, backup_path, zip_gdbs):
                    """
                    Helper function to backup a personal geodatbase
                    """
                    shutil.copyfile(gdb_path, backup_path)
                    arcpy.AddMessage("\t\tBacked up...")

                    _, backup_name = os.path.split(backup_path)

                    if zip_gdbs:
                        with zipfile.ZipFile(backup_path + ".zip", "w") as zf:
                            zf.write(backup_path, backup_name, zipfile.ZIP_DEFLATED)
                        arcpy.AddMessage("\t\tZipped...")

                for gdb_path in gdb_list:
                    _, gdb_extension = os.path.splitext(gdb_path)
                    gdb_basename = os.path.basename(gdb_path)
                    arcpy.AddMessage("\n\t%s:" % gdb_basename)

                    geo_ops_backup_name = backup_timestamp + gdb_basename[4:]  # remove the year
                    geo_ops_backup_path = os.path.join(incident_backups_dir, geo_ops_backup_name)

                    other_backup_name = backup_timestamp + "_" + gdb_basename
                    other_backup_path = os.path.join(incident_backups_dir, other_backup_name)
                    try:
                        if gdb_extension.lower() == '.gdb':  ## A file geodatabase
                            # Only compact file GDBs because arcpro (>=2.7?) crashes when it tries to compact a .mdb
                            arcpy.management.Compact(gdb_path)
                            arcpy.AddMessage("\t\tCompacted...")
                            if gdb_basename.startswith(root_folder_basename):
                                # The gdb has a standard name
                                backup_fgdb(gdb_path, geo_ops_backup_path, zip_gdbs)
                            else:
                                # the gdb has non-standard name
                                backup_fgdb(gdb_path, other_backup_path, zip_gdbs)
                        else:  ## A personal geodatabase
                            if gdb_basename.startswith(root_folder_basename):  ## A standard name
                                backup_mdb(gdb_path, geo_ops_backup_path, zip_gdbs)
                            else:  ## A non-standard name
                                backup_mdb(gdb_path, other_backup_path, zip_gdbs)
                    except Exception as e:  ## Can't compact, back up, or zip the current geodatabase
                        arcpy.AddMessage(
                            "\t*** Cannot process %s because %s" % (gdb_basename, e) +
                            "\n\t*** Check if the geodatabase is locked or in use..."
                        )

            else:  ## No geodatabases were found
                arcpy.AddMessage("\nNo geodatabases were found in incident_data directory: " + incident_data_dir)
        else:  ## The INCIDENT_DATA folder does not exist
            arcpy.AddWarning(
                "\nCan't back up geodatabases because\n" +
                incident_data_dir + " does not exist"
            )

        projects_dir = os.path.join(root_folder, "projects")
        projects_backup_dir = os.path.join(projects_dir, "backups", datestamp)
        # Test for existence of the PROJECTS folder, the BACKUPS folder, and the dated project backup folder.
        if backup_projects:  ## User has opted to back up MXD and APRX files
            if os.path.isdir(projects_dir):  ## Test for existence of the INCIDENT_DATA folder
                if not os.path.isdir(projects_backup_dir):
                    os.makedirs(projects_backup_dir)  ## Create the BACKUPS folder
                    arcpy.AddMessage("\nCreated folder " + projects_backup_dir)

                # Back up MXD projects.
                arcpy.env.workspace = projects_dir
                for search_pattern in ['*.mxd', '*.aprx']:
                    project_filenames = arcpy.ListFiles(search_pattern)  ## Get a list filenames
                    project_type = search_pattern.replace('*.', '').upper()
                    if len(project_filenames) > 0:
                        arcpy.AddMessage("\nProcessing %s files..." % project_type)
                        for filename in project_filenames:
                            arcpy.AddMessage("\n\t%s:" % filename)
                            if root_folder_basename in filename:
                                # Filename follows GeoOps standard convention
                                new_filename = filename.replace(
                                    root_folder_basename,
                                    backup_timestamp + root_folder_basename[4:]
                                )
                                shutil.copyfile(
                                    os.path.join(projects_dir, filename),
                                    os.path.join(projects_backup_dir, new_filename)
                                )
                                arcpy.AddMessage("\t\tBacked up...")
                            else:
                                # non-standard filename
                                new_filename = backup_timestamp + "_" + filename
                                shutil.copyfile(
                                    os.path.join(projects_dir, filename),
                                    os.path.join(projects_backup_dir, new_filename))
                                arcpy.AddMessage("\t\tBacked up...")
                    else:
                        arcpy.AddMessage("\nNo %s files were found" % project_type)

            else:
                arcpy.AddMessage(
                    "\nCan't back up project files because\n" +
                    projects_dir + " does not exist"
                )
        else:
            arcpy.AddMessage("\nProject files were not backed up at the user's request.")

        arcpy.AddMessage(
            "\n\nIncident Periodic Back Up finished in %s\n" % format_elapsed_seconds(time.time() - start_time))


    def execute(self, parameters, messages):
        return self.incident_period_backup(
            root_folder=parameters[0].valueAsText,
            datestamp=parameters[1].valueAsText,
            backup_projects=parameters[2].value,
            zip_gdbs=parameters[3].value
        )  # returns nothing, but that might change in the future


class RoboCopyArchive(object):
    """
    DESCRIPTION:
    This script tool copies all folders and files within a user-specified folder to an
    existing user-specified archive folder.  The initial copy session copies all folders and
    files (a full backup).  Subsequent copy sessions copy only folders and files that are
    new, or that have been modified since the previous copy session (an incremental backup).
    The script will not copy open or locked files (files that are in use).

    REQUIREMENTS:
    ArcGIS 10.x or Pro 2.x at any license level

    USAGE:
    The user must specify an existing source folder, and an existing target folder.

    DISCLAIMER:
    This script is made available for other's use on an "as is" basis, with no warranty,
    either expressed or implied, as to its fitness for any particular purpose.

    AUTHOR:
    Carl Beyerhelm, Circle-5 GeoServices LLC, circle5geo@gmail.com, 928.607.3517
    Updated March, 2021 by Sam Hooper, sam_hooper@firenet.gov

    HISTORY:
    19 Nov 2017 - Develop initial code and test
    20 Nov 2017 - Add code to create time-stamped log files
    04 Dec 2017 - Modify RoboCopy switches
    15 Mar 2021 - Added option to exclude all .lock files - Sam Hooper
    22 Mar 2021 - Migrate to Python toolbox
    """

    def __init__(self):
        self.label = 'RoboCopyArchive'
        self.description = '''
            This script tool copies all folders and files within a user-specified folder to an
            existing user-specified archive folder.  The initial copy session copies all folders and
            files (a full backup).  Subsequent copy sessions copy only folders and files that are
            new, or that have been modified since the previous copy session (an incremental backup).
            The script will not copy open or locked files (files that are in use).
        '''.replace('\n            ', ' ')
        file_path, filename = os.path.split(os.path.abspath(__file__))
        basename, file_ext = os.path.splitext(filename)
        self.stylesheet = os.path.join(file_path, 'docs', 'stylesheets', '%s.%s.pyt.xml' % (basename, self.label))
        # For some reason, Python toolbox tools fail to run in Desktop unless self.canRunInBackground is False
        if not running_from_pro(warning=False):
            self.canRunInBackground = False


    def getParameterInfo(self):
        """
        This method is required by all Python Toolbox tools. It needs to return a list of parameters. Change the order
        here to rearrange the order of parameters in the tool dialog.
        """
        root_dir_path = arcpy.Parameter(
            displayName='''Specify an incident's root folder (like 2017_Boundary)''',
            name='root_dir_path',
            datatype='DEFolder',
            parameterType='Required',
            direction='Input'
        )
        incident_root_dir = find_incident_root_parent_dir()
        if incident_root_dir:
            root_dir_path.value = incident_root_dir

        target_dir = arcpy.Parameter(
            displayName='''Specify an existing target archive folder''',
            name='target_dir',
            datatype='DEFolder',
            parameterType='Required',
            direction='Input'
        )

        exclude_locks = arcpy.Parameter(
            displayName='Exclude all .lock files from the archive',
            name='exclude_locks',
            datatype='GPBoolean',
            parameterType='Required',
            direction='Input'
        )
        exclude_locks.value = True

        return [
            root_dir_path,
            target_dir,
            exclude_locks
        ]


    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        #root_dir_path, date_stamp, backup_projects, zip_gdbs = parameters

        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # Check that the specified incident and target directory exist
        root_dir_path, target_dir_path, exclude_locks = parameters
        if root_dir_path.value:
            if not os.path.isdir(root_dir_path.valueAsText):
                root_dir_path.setErrorMessage('The specified path does not exist or is not a directory')
            else:
                root_dir_path.clearMessage()

        if target_dir_path.value:
            if not os.path.isdir(target_dir_path.valueAsText):
                target_dir_path.setErrorMessage('The specified path does not exist or is not a directory')
            else:
                target_dir_path.clearMessage()

        return


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True


    def robo_copy_archive(self, source_dir=None, target_dir=None, exclude_locks=False):
        """
        Helper function to be able to call script from either Toolbox dialog or command line with other arguments
        """
        start_time = time.time()

        arcpy.AddMessage("\n\nRoboCopy Archive was developed by Carl Beyerhelm, Sundance Consulting Inc.\n")

        # Issue warning if running from Desktop
        running_from_pro()

        # Check that the source and target exist
        if not os.path.isdir(source_dir):
            raise IOError('The root incident directory specified does not exist: \n' + source_dir)
        if not os.path.isdir(target_dir):
            raise IOError('The target archive directory specified does not exist: \n' + target_dir)

        arcpy.env.workspace = target_dir

        # if the archive dir doesn't exist, create it
        archive_dir = os.path.join(target_dir, 'ArchiveLogs')
        if not os.path.isdir(archive_dir):
            os.mkdir(archive_dir)
            arcpy.AddMessage("\nCreated the ArchiveLogs folder...")

        # Run RoboCopy using specified source and target folders.
        log_path = os.path.join(archive_dir, 'robocopy_log_%s.txt' % time.strftime("%Y%m%d_%H%M"))
        arcpy.AddMessage("\nArchive session in progress.  Please standby...\n")
        robocopy_args = ["robocopy", source_dir, target_dir, "/E", "/FFT", "/NP", "/NS", "/NDL", "/TEE", "/XX", "/R:1",
                         "/W:1", "/LOG:" + log_path]
        if exclude_locks:
            robocopy_args += ["/XF", "*.lock"]

        # Call the RoboCopy command without blocking so the script will continue
        process = subprocess.Popen(robocopy_args)

        # If lock files were excluded, warn the user if any .lock files do exist
        if exclude_locks:
            lock_files = []
            for root, dirs, files in os.walk(source_dir):
                lock_files.extend([os.path.join(root, f).replace(source_dir, '.') for f in files if f[-5:] == '.lock'])
            if len(lock_files) > 0:
                arcpy.AddWarning(
                    'The following lock files were found in the directory tree but will be not be copied to the archive:\n\t' + \
                    '\n\t'.join(lock_files)
                )

        # Now start blocking until RoboCopy is done (if it isn't already finished)
        process.wait()

        arcpy.AddMessage("\nRoboCopy Archive finished in %s\n" % format_elapsed_seconds(time.time() - start_time))
        arcpy.AddMessage("\nThe log file was written to %s\n\n" % log_path)

        # Open the log file
        os.startfile(log_path)

        return


    def execute(self, parameters, messages):
        return self.robo_copy_archive(
            source_dir=parameters[0].valueAsText,
            target_dir=parameters[1].valueAsText,
            exclude_locks=parameters[2].value
        )  # returns nothing, but that might change in the future



class FireProgression(object):
    """
    DESCRIPTION:
    This script tool copies all folders and files within a user-specified folder to an
    existing user-specified archive folder.  The initial copy session copies all folders and
    files (a full backup).  Subsequent copy sessions copy only folders and files that are
    new, or that have been modified since the previous copy session (an incremental backup).
    The script will not copy open or locked files (files that are in use).

    REQUIREMENTS:
    ArcGIS 10.x or Pro 2.x at any license level

    USAGE:
    The user must specify an existing source folder, and an existing target folder.

    DISCLAIMER:
    This script is made available for other's use on an "as is" basis, with no warranty,
    either expressed or implied, as to its fitness for any particular purpose.

    AUTHOR:
    Carl Beyerhelm, Circle-5 GeoServices LLC, circle5geo@gmail.com, 928.607.3517
    Updated March, 2021 by Sam Hooper, sam_hooper@firenet.gov

    HISTORY:
    19 Nov 2017 - Develop initial code and test
    20 Nov 2017 - Add code to create time-stamped log files
    04 Dec 2017 - Modify RoboCopy switches
    15 Mar 2021 - Added option to exclude all .lock files - Sam Hooper
    22 Mar 2021 - Migrate to Python toolbox
    """

    def __init__(self):
        self.label = 'RoboCopyArchive'
        self.description = '''
            This script tool copies all folders and files within a user-specified folder to an
            existing user-specified archive folder.  The initial copy session copies all folders and
            files (a full backup).  Subsequent copy sessions copy only folders and files that are
            new, or that have been modified since the previous copy session (an incremental backup).
            The script will not copy open or locked files (files that are in use).
        '''.replace('\n            ', ' ')
        file_path, filename = os.path.split(os.path.abspath(__file__))
        basename, file_ext = os.path.splitext(filename)
        self.stylesheet = os.path.join(file_path, 'docs', 'stylesheets', '%s.%s.pyt.xml' % (basename, self.label))
        # For some reason, Python toolbox tools fail to run in Desktop unless self.canRunInBackground is False
        if not running_from_pro(warning=False):
            self.canRunInBackground = False


    def getParameterInfo(self):
        """
        This method is required by all Python Toolbox tools. It needs to return a list of parameters. Change the order
        here to rearrange the order of parameters in the tool dialog.
        """
        event_geodatabase = arcpy.Parameter(
            displayName='''Specify the incident's Event geodatabase''',
            name='event_geodatabase',
            datatype='DEWorkspace',
            parameterType='Required',
            direction='Input'
        )

        spatial_reference = arcpy.Parameter(
            displayName='''Specify the incident's projected spatial reference''',
            name='spatial_reference',
            datatype='GPSpatialReference',
            parameterType='Required',
            direction='Input'
        )

        exclude_locks = arcpy.Parameter(
            displayName='Exclude all .lock files from the archive',
            name='exclude_locks',
            datatype='GPBoolean',
            parameterType='Required',
            direction='Input'
        )
        exclude_locks.value = True

        return [
            root_dir_path,
            target_dir,
            exclude_locks
        ]


    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        #root_dir_path, date_stamp, backup_projects, zip_gdbs = parameters

        return


    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # Check that the specified incident and target directory exist
        root_dir_path, target_dir_path, exclude_locks = parameters
        if root_dir_path.value:
            if not os.path.isdir(root_dir_path.valueAsText):
                root_dir_path.setErrorMessage('The specified path does not exist or is not a directory')
            else:
                root_dir_path.clearMessage()

        if target_dir_path.value:
            if not os.path.isdir(target_dir_path.valueAsText):
                target_dir_path.setErrorMessage('The specified path does not exist or is not a directory')
            else:
                target_dir_path.clearMessage()

        return


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True


    def robo_copy_archive(self, source_dir=None, target_dir=None, exclude_locks=False):
        """
        Helper function to be able to call script from either Toolbox dialog or command line with other arguments
        """


        try:
        arcpy.AddMessage(
            "\n\n" + "Update Fire Progression was developed by Carl Beyerhelm, Circle-5 GeoServices LLC." + "\n")

        # Accept user inputs.
        eventGDB = arcpy.GetParameterAsText(0)  ## The incident's Event geodatabase
        inSR = arcpy.GetParameter(1)  ## The incident's user-specified spatial reference
        fcInputs = arcpy.GetParameterAsText(2)  ## A date-ordered list of fire perimeter polygons
        clipOK = arcpy.GetParameterAsText(3)  ## A flag to clip previous inputs with subsequent inputs
        startDate = arcpy.GetParameterAsText(5)  ## A starting date for consecutively dated inputs

        # Set variables.
        gdb_basename, _ = os.path.splitext(eventGDB)
        progGDB = gdb_basename + "_progression.gdb"  ## A name for the fire progression GDB
        dataFolder = os.path.dirname(eventGDB)  ## The INCIDENT_DATA folder
        progFolder = os.path.join(dataFolder, "progression")  ## The PROGRESSION folder
        inWKID = inSR.factoryCode  ## Establish the incident's spatial reference WKID

        # Establish default workspace and set environment.
        if not os.path.isdir(progFolder):  ## If there is no PROGRESSION folder
            os.mkdir(progFolder)  ## Create the PROGRESSION folder
        arcpy.env.workspace = progFolder  ## Establish the folder workspace
        if not arcpy.Exists(progGDB):  ## If there is no progression GDB
            arcpy.CreateFileGDB_management(progFolder, progGDB)  ## Create the progression GDB
        arcpy.env.workspace = os.path.join(progFolder, progGDB)  ## Establish the GDB workspace
        arcpy.env.overwriteOutput = True

        # Prepare for date arithmetic.
        if startDate:  ## If a start date has been specified
            startDate = startDate.split(" ")[0]  ## The date-only portion of startDate
            dateParts = startDate.split("/")  ## Parse startDate into its component parts
            dateObject = datetime.date(int(dateParts[2]), int(dateParts[0]),
                                       int(dateParts[1]))  ## Create a date object
            dateChange = datetime.timedelta(days=1)  ## Set the date increment value to 1 day

        # Validate user inputs.
        arcpy.AddMessage("\nValidating user inputs...")
        fcList = fcInputs.split(";")  ## Parse fcInputs into a Python list
        inputCount = len(fcList)  ## Get a count of list elements
        if inputCount < 2:  ## Test if 2, or more, feature class inputs were specified
            arcpy.AddError(
                "\nFATAL - At least two polygon inputs must be specified but only %s given..." % inputCount)
            sys.exit()

        for fc in fcList:
            # Test if any inputs have spaces in their path or file name
            if " " in fc:
                ##### Copy to temporary file without spaces
                arcpy.AddError("\n" + "FATAL - " + fc + "\n"
                                                        "must not have spaces in its path or filename...")
                sys.exit()

            # Add a valid PROG_DATE field to any input that doesn't have a field named PROG_DATE
            fieldList = arcpy.ListFields(fc, "prog_date")  ## Create a list of fields named "prog_date"
            if not fieldList:  ## If the current feature class doesn't have a PROG_DATE field
                arcpy.AddField_management(fc, "prog_date", "TEXT", "#", "#", "15")  ## Add a PROG_DATE field
                arcpy.AddMessage("\n" + "Added a PROG_DATE field to " + os.path.basename(fc) + "...")

            #### Pretty sure this is superfluous because the next test would ensure the input FC is projected
            descFC = arcpy.Describe(fc)
            if descFC.SpatialReference.Type.lower() != "projected":  ## Test if each feature class input is projected
                arcpy.AddError("\n" + "FATAL - " + os.path.basename(fc) + "\n"
                                                                          "must have a projected coordinate system...")
                sys.exit()

            fcWKID = descFC.SpatialReference.factoryCode
            if fcWKID != inWKID:  ## Test if each feature class input matches the incident's spatial reference
                #### Project on  the fly
                arcpy.AddError("\n" + "FATAL - " + os.path.basename(fc) + "\n"
                                                                          "must match the incident's spatial reference, WKID " + str(
                    inWKID) + "...")
                sys.exit()
            if descFC.ShapeType != "Polygon":  ## Test if each feature class input has a polygon shape type
                arcpy.AddError("\n" + "FATAL - " + os.path.basename(fc) + "\n"
                                                                          "must have a polygon shape type...")
                sys.exit()
            fieldList = arcpy.ListFields(fc, "prog_date")  ## Create a list of fields named "prog_date"
            for field in fieldList:
                if field.type.lower() != "string":  ## Test if the PROG_DATE field type is TEXT
                    arcpy.AddError("\n" + "FATAL - The PROG_DATE field in " + os.path.basename(fc) + "\n"
                                                                                                     "must be a TEXT type field...")
                    sys.exit()
                if field.length < 15:  ## Test if the PROG_DATE field length is < 15
                    arcpy.AddError("\n" + "FATAL - The PROG_DATE field in " + os.path.basename(fc) + "\n"
                                                                                                     "must have a length of at least 15 characters...")
                    sys.exit()
                if not startDate:  ## Test if a starting date was not specified
                    rows = arcpy.SearchCursor(fc)
                    for row in rows:
                        if row.prog_date in (
                        "", " ", None):  ## Test if the PROG_DATE field value is a zero-length string or is NULL
                            arcpy.AddError("\n" + "FATAL - The PROG_DATE field in " + os.path.basename(fc) + "\n"
                                                                                                             "must be populated like 'YYYY-MM-DD' if a starting date is not specified...")
                            del row, rows  ## Release the row and table locks
                            sys.exit()
        arcpy.AddMessage("\nAll user inputs are valid...")

        # Delete scratch files, if they exist.
        arcpy.AddMessage("\n" + "Deleting scratch files, if they exist...")
        scratchFCs = arcpy.ListFeatureClasses("xxProg*", "Polygon")
        for fc in scratchFCs:
            arcpy.Delete_management(fc)

        # Copy the first feature class input to xxProg0.
        arcpy.AddMessage("\nProcessing inputs...")
        arcpy.AddMessage("   > " + os.path.basename(fcList[0]) + "...")
        arcpy.CopyFeatures_management(fcList[0], os.path.join(progFolder, progGDB, "xxProg0"))

        # If an unbroken series of progression dates was indicated by the user, calculate PROG_DATE as the starting date of that series.
        if startDate:
            arcpy.CalculateField_management("xxProg0", "prog_date", '"' + dateObject.strftime("%Y-%m-%d") + '"')

        # Cycle through each of the remaining feature class inputs.
        for index in range(1, inputCount):  ##### change to enumerate
            arcpy.AddMessage("   > " + os.path.basename(fcList[index]) + "...")
            arcpy.CopyFeatures_management(fcList[index], os.path.join(progFolder, progGDB,
                                                                      "xxProgTemp"))  ## Copy the current feature class input to xxProgTemp

            # If an unbroken series of progression dates was indicated by the user, calculate PROG_DATE as the next date in that series.
            if startDate:
                dateObject = dateObject + dateChange  ## Increment the date by 1 day
                arcpy.CalculateField_management("xxProgTemp", "prog_date",
                                                '"' + dateObject.strftime("%Y-%m-%d") + '"')

            # Perform the CLIP (if applicable) and UNION procedure(s).
            if clipOK == "true":
                arcpy.Clip_analysis("xxProg" + str(index - 1), "xxProgTemp",
                                    "xxProg" + str(index - 1) + "Clip")  ## Clip prior period with current period
                arcpy.Union_analysis(["xxProgTemp", "xxProg" + str(index - 1) + "Clip"], "xxProg" + str(index),
                                     "NO_FID")  ## Union current period with clipped prior period
            else:
                arcpy.Union_analysis(["xxProgTemp", "xxProg" + str(index - 1)], "xxProg" + str(index),
                                     "NO_FID")  ## Union current period with prior period
            arcpy.Delete_management("xxProgTemp")
        arcpy.CopyFeatures_management("xxProg" + str(index), "xxProg_Output")

        # Calculate the PROG_DATE field value for each record in xxProg_Output to be
        # the earliest (lowest) non-blank date value from among all of the unioned date fields.
        arcpy.AddMessage("\n" + "Compiling dates...")
        fieldList = arcpy.ListFields("xxProg_Output", "prog_date*")
        fieldNames = ""
        for field in fieldList:  ## For each PROG_DATE field in xxProg_Output
            fieldNames = fieldNames + "!" + field.name + "!,"  ## Build a list of all of the PROG_DATE field names
            xPression = "findZLSN(!" + field.name + "!)"  ## Set PROG_DATE fields with a zero-length string or NULL value to "9999-99-99-9999"
            arcpy.CalculateField_management("xxProg_Output", field.name, xPression, "PYTHON_9.3", codeBlock2)
        fieldNames = fieldNames[0:-1]  ## Strip off the trailing comma
        arcpy.CalculateField_management("xxProg_Output", "prog_date", 'min(' + fieldNames + ')',
                                        "PYTHON_9.3")  ## Calculate PROG_DATE as the earliest date

        # Find the progression's most recent (largest) date, and use it as part of the progression feature class name.
        rows = arcpy.SearchCursor("xxProg_Output")
        maxDate = "0000-00-00-0000"
        for row in rows:
            if row.prog_date >= maxDate:
                maxDate = row.prog_date
        del row, rows  ## Release the row and table locks
        maxDate = maxDate.replace("-", "")
        progFcName = progGDB.replace("-", "")
        outFC = "i_" + maxDate + progFcName[4:-4]  ## A name for the output progression feature class
        outXls = os.path.join(progFolder, outFC[2:] + ".xls")  ## The output summary table in Excel format

        # Dissolve xxProg_Output on the PROG_DATE field to produce outFC.
        arcpy.Dissolve_management("xxProg_Output", outFC, ["prog_date"])
        arcpy.AlterField_management(outFC, "prog_date", "#", "Date")  ## Rename the PROG_DATE field to DATE

        # Add the GROWTH_AC, TOTAL_AC, and LEGEND_TEXT fields to outFC, and calculate their values.
        arcpy.AddMessage("\n" + "Calculating growth and total acres...")
        arcpy.AddField_management(outFC, "growth_ac", "DOUBLE", "#", "#", "#",
                                  "Growth Ac")  ## Add a GROWTH_AC numeric field
        arcpy.AddField_management(outFC, "total_ac", "LONG", "#", "#", "#",
                                  "Total Ac")  ## Add a TOTAL_AC numeric field
        arcpy.AddField_management(outFC, "legend_text", "TEXT", "#", "#", "50",
                                  "Legend Text")  ## Add a LEGEND_TEXT text field
        arcpy.AddField_management(outFC, "tmp_Growth", "TEXT", "#", "#", "15",
                                  "Temp Growth")  ## Add a temporary TMP_GROWTH text field
        arcpy.AddField_management(outFC, "tmp_Total", "TEXT", "#", "#", "15",
                                  "Temp Total")  ## Add a temporary TMP_TOTAL text field

        # Calculate GROWTH_AC.
        arcpy.CalculateField_management(outFC, "growth_ac", "!shape.area@acres!", "PYTHON_9.3")

        # Calculate TOTAL_AC as a running sum of GROWTH_AC, and then round GROWTH_AC to a whole number.
        xPression = "accumulateTotal(!growth_ac!)"
        arcpy.CalculateField_management(outFC, "total_ac", xPression, "PYTHON_9.3", codeBlock1)
        arcpy.CalculateField_management(outFC, "growth_ac", "round(!growth_ac!, 0)", "PYTHON_9.3")

        # Find the maximum GROWTH_AC and TOTAL_AC field values.
        with arcpy.da.SearchCursor(outFC, ["growth_ac"]) as rows:  ## Find the max value in the GROWTH_AC field
            maxGroAc = 0
            for row in rows:
                if row[0] > maxGroAc:
                    maxGroAc = int(round(row[0], 0))  ## Round and make an integer of maxGroAc
                    lenGroAc = len(str(maxGroAc))  ## Cast maxGroAc as a string and find its length
        with arcpy.da.SearchCursor(outFC, ["total_ac"]) as rows:  ## Find the max value in the TOTAL_AC field
            maxTotAc = 0
            for row in rows:
                if row[0] > maxTotAc:
                    maxTotAc = row[0]
                    lenTotAc = len(str(maxTotAc))  ## Cast maxTotAc as a string and find its length

        # Define a dictionary that returns the number of text spaces required for a number that includes thousands separators.
        dict = {1: 1, 2: 2, 3: 3, 4: 5, 5: 6, 6: 7, 7: 9, 8: 10, 9: 11, 10: 12}

        # Calculate TMP_GROWTH and TMP_TOTAL fields as text representations of their corresponding numeric value
        # with enough right-justification to accommodate the largest number.  Then, incorporate those right-justified
        # text values into the LEGEND_TEXT field.  This is done to improve readability of the LEGEND_TEXT field.
        expGro = "'{0:,.0f}'.format(!growth_ac!).rjust(" + str(dict[lenGroAc]) + ")"
        expTot = "'{0:,.0f}'.format(!total_ac!).rjust(" + str(dict[lenTotAc]) + ")"
        arcpy.CalculateField_management(outFC, "tmp_Growth", expGro, "PYTHON_9.3")
        arcpy.CalculateField_management(outFC, "tmp_Total", expTot, "PYTHON_9.3")
        arcpy.CalculateField_management(outFC, "legend_text",
                                        '!prog_date! + "  " + !tmp_Growth! + " growth ac  " + !tmp_Total! + " total ac"',
                                        "PYTHON_9.3")

        # Delete the temporary TMP_GROWTH and TMP_TOTAL fields.
        arcpy.DeleteField_management(outFC, "tmp_Growth")
        arcpy.DeleteField_management(outFC, "tmp_Total")

        # Write outFC's table to Excel format.
        arcpy.AddMessage("\n" + "Writing an acreage summary table to Excel...")
        arcpy.TableToExcel_conversion(outFC, outXls, "ALIAS")

        # Signal successful completion.
        # arcpy.RefreshCatalog(progFolder)  ## Refresh the ArcMap catalog view...not supported in ArcPro
        arcpy.AddMessage("\n" + "OK, done!")
        arcpy.AddMessage("\n" + "The new fire progression feature class is filed as:")
        arcpy.AddMessage("   > " + progFolder + "\\")
        arcpy.AddMessage("        " + os.path.join(progGDB, outFC))
        arcpy.AddMessage("\n" + "The new fire progression summary Excel table is filed as:")
        arcpy.AddMessage("   > " + os.path.dirname(outXls) + "\\")
        arcpy.AddMessage("        " + os.path.basename(outXls))

        '''except SystemExit:
            pass
        except:
            arcpy.AddError("\n" + arcpy.GetMessages(2) + "\n")

        finally:
            # Delete all scratch files, and finish up.
            arcpy.AddMessage("\n" + "Deleting scratch files...")
            scratchFCs = arcpy.ListFeatureClasses("xxProg*", "Polygon")
            for fc in scratchFCs:
                arcpy.Delete_management(fc)
            arcpy.AddMessage("\n")'''

        return


    def execute(self, parameters, messages):
        return self.robo_copy_archive(
            source_dir=parameters[0].valueAsText,
            target_dir=parameters[1].valueAsText,
            exclude_locks=parameters[2].value
        )  # returns nothing, but that m




########################################################################################################################
#----------------------------------------- Utilities -------------------------------------------------------------------
########################################################################################################################


def running_from_cli():
    """
    Helper function to check if the script is being run from the command line or from an ArcToolbox
    dialog
    """
    if arcpy.GetInstallInfo()['ProductName'] == "Desktop":
        try:
            arcpy.mapping.MapDocument("Current")
        except:
            return True
    else:
        try:
            arcpy.mp.ArcGISProject("Current")
        except:
            return True

    return False


def running_from_pro(warning=True):
    """
    Helper function to determine if the user is running the script/tool from ArcGIS Pro or Desktop
    :param warning: Boolean flag indicating whether or not to issue a warning if the tool is run from ArcGIS Desktop
    :return: Boolean indicating whether the tool is being run from ArcGIS Pro or not
    """

    if arcpy.GetInstallInfo()['ProductName'] == "Desktop":
        # Warn the user that ArcGIS Desktop is no longer supported
        if warning:
            arcpy.AddWarning(
                'This tool no longer supports ArcGIS Desktop. Although it might work,' 
                ' there is no guarantee of the results. Please run this tool from the'
                ' currently recommended version of ArcGIS Pro\n'
            )
        return False
    else:
        return True


def format_elapsed_seconds(elapsed_seconds):
    """
    Helper function to convert number of seconds to a string of hours, minutes, and seconds
    :param elapsed_seconds: float or int of the number of elapse seconds to format into a string
    :return: formatted time string
    """

    hours = int(elapsed_seconds / 3600.0)
    minutes = int(elapsed_seconds / 60.0 % 60)
    seconds = elapsed_seconds % 60.0

    time_string = '{:0.0f} hour{}, '.format(hours, 's' if hours != 1 else '') if hours >= 1 else ''
    time_string += '{:0.0f} minute{}, and '.format(minutes, 's' if minutes != 1 else '') if minutes >= 1 else ''
    time_string += '{:0.0f} second{}'.format(seconds, 's' if int(seconds) != 1 else '')

    return time_string


def in_incident_root(current_dir_path):
    """
    Helper function to determine if a sub directory is a child of an incident directory. This is useful for setting
    default params in tools that has an incident directory as an input
    :param current_dir_path: String of the path being evaluated
    :return: tuple of (parent directory path, boolean indicating if the parent directory matches the incident dir pattern)
    """

    parent_dir_path, current_dir_name = os.path.split(current_dir_path)
    is_root_dir = False
    if current_dir_name == 'tools':
        parent_dir_name = os.path.basename(parent_dir_path)
        if re.match(r'\d{4}_[a-zA-Z]*', parent_dir_name):
            is_root_dir = True

    return parent_dir_path.lower(), is_root_dir


def find_incident_root_parent_dir():
    """
    If this folder is contained within a folder called "tools", check if "tools"
    parent dir follows the GeoOps standard for the root dir of the incident
    folder structure. If so, set it as the default path
    :return: The full path to the incident root directory if found. Otherwise, return None
    """


    current_dir_path = os.path.abspath(__file__)
    drive, _ = os.path.splitdrive(current_dir_path)
    drive += os.sep

    parent_dir_path, is_root_dir = in_incident_root(current_dir_path)
    i = 1
    while parent_dir_path != drive and not is_root_dir and i < WINDOWS_MAX_PATH_LENGTH:
        parent_dir_path, is_root_dir = in_incident_root(parent_dir_path)
        if is_root_dir:
            return parent_dir_path
        i += 1



########################################################################################################################
#----------------------------------------- Command line gateway --------------------------------------------------------
########################################################################################################################
if __name__ == '__main__' and running_from_cli():
    r"""
    To run from the command line, call as you would any other script except make the first argument the class name of 
    the tool you want to run. For instance, to run RoboCopyArchive, call the script as
        python community_giss_toolbox_standard.pyt RoboCopyArchive c:\path\to\incident\root c:\path\to\target\archive 
    """
    FUNCTIONS = {
        'CalculateGeometryAttributes': CalculateGeometryAttributes().calculate_geometry_attributes,
        'CalculateContainment': CalculateContainment().calculate_containment,
        'IncidentPeriodBackup': IncidentPeriodBackup().incident_period_backup,
        'RoboCopyArchive': RoboCopyArchive().robo_copy_archive
    }

    tool_name = sys.argv[1]
    if tool_name in FUNCTIONS:
        FUNCTIONS[tool_name](*sys.argv[2:])
    else:
        raise ValueError(
            'No tool named {0}. Options include:\n\t{1}'.format(tool_name, '\n\t'.join(FUNCTIONS.keys()))
        )