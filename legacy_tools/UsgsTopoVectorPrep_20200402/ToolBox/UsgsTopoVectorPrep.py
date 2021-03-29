#=========================================================================================
# SCRIPT
# UsgsTopoVectorPrep.py
#
# DESCRIPTION
# This ArcGIS 10.x script tool:
# > Downloads or copies, unzips, clips, and combines quad-sized USGS topo vector
#   geodatabases from either online or local sources into a single file geodatabase for
#   use as a topo vector background map in ArcGIS
# > Dissolves line and polygon features that were split across quad frames
# > Re-sources a LYR file to the new USGS topo vector GDB to symbolize its features
# > Optionally, projects the GCS_North_American_1983 feature classes into a user-specified
#   spatial reference using the tool's built-in "Output Coordinates" environment setting
#
# USAGE
# Within the script tool's dialog, users must specify five items:
# > Whether topo vector GDBs will come from an online source, or from a local source
# > A local folder containing topo vector GDBs (if a local source was specified)
# > A folder to contain the downloaded or copied topo vector GDBs and final GDB output
# > An AOI feature class
# > A buffer distance to apply to the AOI feature class (optional)
#
# DISCLAIMER
# This script is made available for other's use on an "as is" basis, with no warranty,
# either expressed or implied, as to its fitness for any particular purpose.
#
# AUTHOR
# Carl Beyerhelm, Circle-5 GeoServices LLC, circle5geo@gmail.com, 928.607.3517
#
# HISTORY
# 13 Jun 2018 - Initial coding and testing
# 14 Jun 2018 - Clean up scripting elements, and add in-line documentation
# 15 Jun 2018 - Add code to dissolve polygon features that were split across quad frames
# 19 Jul 2018 - Add code to dissolve line features that were split across quad frames
# 19 Jul 2018 - Add code to unzip USGS topo vector downloads
# 04 Aug 2018 - Add code to download zipped USGS topo vector GDBs directly (bypass uGet)
#               using the text file list of URLs from the USGS National Map (TNM) site
# 14 Aug 2018 - Add code to select the clipping frame by attribute instead of by location
#               to fix an issue with processing coastal quads
# 21 Aug 2018 - Add code to permit either download or copy of topo vector data from either
#               an online source or local source, as adapted from Matt Panunto USFS
# 23 Aug 2018 - Add tool validator code to calculate the number of 7.5-minute quads that
#               will be retrieved by the combination of AOI and AOI buffer distance
# 25 Aug 2018 - Add code to re-source a LYR file to the new USGS topo vector GDB to
#               symbolize its features
# 26 Aug 2018 - Package the tool as an add-in
# 21 Jun 2019 - Revise code to select the clipLyr feature from the UsgsQuadIndex_75Minute
#               feature class instead of from the CellGrid_7_5Minute feature class in
#               order to improve quad name matching for those having an apostrophe in
#               their quad name
# 06 Jul 2019 - Revise DISSOLVE processing to be based on a Python dictionary containing
#               dissolve fields that are explicitly matched to each feature class
# 06 Jul 2019 - Add code to construct consistent labels for Township, Range, and Section
# 28 Jul 2019 - Add code to display progress as an X of Y countdown
# 28 Jul 2019 - Add code to quit if the number of USGS topo vector downloads is zero
# 18 Oct 2019 - Add code to strip measures from NhdFlowline to prevent potential measures
#               out-of-bounds error
# 20 Nov 2019 - Add code to strip leading zeros from section numbers to create a section
#               label field
# 04 Jan 2020 - Add code to strip leading zeros from township and range numbers to create
#               a township and range label field
# 16 Feb 2020 - Added a Python dictionary DISSOLVE parameter for the Trans_RoadSegment FC
# 02 Apr 2020 - Add code to more explicitly declare the current workspace
#=========================================================================================
import arcpy, os, sys, time, urllib, zipfile

try:
    arcpy.AddMessage("\n\n" + "USGS Topo Vector Prep was developed by Carl Beyerhelm, Circle-5 GeoServices LLC")
    arcpy.AddMessage("Portions adapted from Matt Panunto, DOI-BLM")

    # Accept user input and set environments.
    topoSource      = arcpy.GetParameterAsText(0)  ## Specify whether topo data are "Local" or "Online"
    localTopoFolder = arcpy.GetParameterAsText(1)  ## If topo data are local, specify the parent folder containing topo data organized by state abbreviation
    outputFolder    = arcpy.GetParameterAsText(2)  ## Specify the parent folder where topo data will be downloaded or copied to, unzipped, and processed into a final fGDB
    aoiFc           = arcpy.GetParameterAsText(3)  ## Specify the AOI polygon layer
    searchDistance  = arcpy.GetParameterAsText(4)  ## Specify the AOI polygon search distance
    downloadFolder  = os.path.join(outputFolder, "TopoDownloads")  ## The folder where topo data will be downloaded or copied to
    timeStamp       = time.strftime("%Y%m%d") + "_" + time.strftime("%H%M")  ## A date/time stamp
    topoIndex       = os.path.join(os.path.dirname(__file__), "UsgsQuadIndex_75Minute.gdb\\UsgsQuadIndex_75Minute")  ## The 7.5-minute topo index polygon layer
    arcpy.env.overwriteOutput = True
    arcpy.env.addOutputsToMap = False

    # Select topoIndex features that are within searchDistance of aoiFc.
    arcpy.AddMessage("\n\n" + "Selecting USGS 7.5-minute vector topo GDBs within " + searchDistance + " of AOI features...")
    arcpy.MakeFeatureLayer_management(topoIndex, "topoLyr")
    arcpy.SelectLayerByLocation_management("topoLyr", "WITHIN_A_DISTANCE", aoiFc, searchDistance, "NEW_SELECTION")

    # Create Python lists of each selected quad's primary state abbreviation and URL.
    primaryStateList = []
    urlList = []
    with arcpy.da.SearchCursor("topoLyr", ["PRIM_ABRV", "URL"]) as cursor:
        for row in cursor:
            primaryStateList.append(row[0])
            urlList.append(row[1])
    arcpy.SelectLayerByAttribute_management("topoLyr", "CLEAR_SELECTION")  ## Clear the selection
    arcpy.Delete_management("topoLyr")  ## Dismiss topoLyr
    urlCount = len(urlList)

    # Delete downloadFolder (if it exists), and then recreate it.
    if arcpy.Exists(downloadFolder):
        arcpy.Delete_management(downloadFolder)
    arcpy.CreateFolder_management(outputFolder, "TopoDownloads")

    # Download selected topo data from online USGS source.
    if topoSource == "Online":
        arcpy.AddMessage("\n" + "Downloading:")
        for i in range(0, urlCount):
            try:
                urllib.urlretrieve(urlList[i], os.path.join(downloadFolder, os.path.basename(urlList[i])))
                urllib.urlcleanup()  ## Clear the download cache
                arcpy.AddMessage("   "                      + str(i + 1) + " of " + str(urlCount) + " " + os.path.basename(urlList[i]))
            except:
                arcpy.AddMessage("   !! Couldn't download " + str(i + 1) + " of " + str(urlCount) + " " + os.path.basename(urlList[i]))
                pass

    # Copy selected topo data from localTopoFolder.
    else:
        arcpy.AddMessage("\n" + "Copying:")
        for i in range(0, urlCount):
            try:
                arcpy.Copy_management(os.path.join(localTopoFolder, primaryStateList[i], os.path.basename(urlList[i])),
                                      os.path.join(downloadFolder, os.path.basename(urlList[i])))
                arcpy.AddMessage("   "                  + str(i + 1) + " of " + str(urlCount) + " " + os.path.basename(urlList[i]))

            except:
                arcpy.AddMessage("   !! Couldn't copy " + str(i + 1) + " of " + str(urlCount) + " " + os.path.basename(urlList[i]))
                pass

    # Unzip the USGS topo vector downloads.
    arcpy.env.workspace = downloadFolder
    arcpy.AddMessage("\n" + "Unzipping...")
    fileList = arcpy.ListFiles("*.zip")
    zipCount = len(fileList)
    if zipCount == 0:
        arcpy.AddMessage("\n" + "Can't continue!!  No USGS topo vector GDBs were downloaded or copied.")
        sys.exit()
    for i in range(0, zipCount):
        zip = zipfile.ZipFile(os.path.join(downloadFolder, fileList[i]))
        zip.extractall(downloadFolder)
        arcpy.AddMessage("   " + str(i + 1) + " of " + str(zipCount) + " " + fileList[i])

    # Create the output GDB.
    arcpy.AddMessage("\n" + "Creating the output fGDB...")
    outGdb = "Aoi_VectorTopo_" + timeStamp + ".gdb"
    arcpy.CreateFileGDB_management(outputFolder, outGdb)

    # Copy or append the feature classes from each of the USGS topo vector GDBs into a new fGDB.
    arcpy.MakeFeatureLayer_management(topoIndex, "clipLyr")  ## Make a feature layer from topoIndex
    gdbList = arcpy.ListWorkspaces("VECTOR_*", "FileGDB")  ## Get a list of the 7.5-minute USGS topo vector GDBs
    gdbCount = len(gdbList)
    for i in range(0, gdbCount):  ## For each of the USGS topo vector GDBs
        arcpy.AddMessage("\n" + "Processing " + str(i + 1) + " of " + str(gdbCount) + " " + gdbList[i] + "...")
        arcpy.env.workspace = gdbList[i]  ## Set the home workspace to the current vector topo GDB

        # Get the clipLyr quad ID from the current GDB name.
        gdbName = os.path.basename(gdbList[i])
        quadId  = gdbName.replace(".gdb", ".zip")  ## The quadId value will be used to select a clipLyr feature based on its BASENAME field

        # Select the current GDB's corresponding quad frame to act as a clipping polygon.
        arcpy.SelectLayerByAttribute_management("clipLyr", "NEW_SELECTION", "BASENAME = '" + quadId + "'")  ## Select the GDB's corresponding quad frame

        dsList = arcpy.ListDatasets("", "Feature")  ## Get a list of feature datasets in the current GDB
        dsList = [''] + dsList if dsList is not None else []  ## Addition of the empty string permits stand-alone feature classes to be discovered

        for ds in dsList:  ## For each of the feature datasets within the current GDB
            arcpy.AddMessage("   Feature dataset " + ds + "...")
            arcpy.env.workspace = os.path.join(gdbList[i], ds)  ## Set the home workspace to the current feature dataset
            fcList = arcpy.ListFeatureClasses("*")  ## Get a list of feature classes within the current feature dataset
            for fc in fcList:  ## For each of the feature classes within the current feature dataset
                if fc == "NHDFlowline":                            ## If the current fc is NhdFlowline
                    arcpy.env.outputMFlag = "Disabled"             ## Strip measures from NhdFlowline to prevent measures out-of-bounds error
                    arcpy.CopyFeatures_management (fc, fc + "xx")  ## Copy fc to fcxx
                    arcpy.Delete_management(fc)                    ## Delete fc
                    arcpy.Rename_management(fc+"xx", fc)           ## Rename fcxx to fc
                arcpy.AddMessage("      Feature class " + fc)
                if not arcpy.Exists(os.path.join(outputFolder, outGdb, fc)):  ## If the target feature class doesn't exist yet
                    arcpy.Clip_analysis(fc, "clipLyr", os.path.join(outputFolder, outGdb, fc))  ## Clip the current feature class into the target feature class
                else:
                    arcpy.Clip_analysis(fc, "clipLyr", "in_memory\\clippedData")  ## Clip the current feature class to an in_memory object
                    arcpy.Append_management("in_memory\\clippedData", os.path.join(outputFolder, outGdb, fc), "NO_TEST")  ## Append the in_memory object into the target feature class
                    arcpy.Delete_management("in_memory\\clippedData")  ## Delete the in_memory object
    arcpy.Delete_management("clipLyr")  ## Dismiss clipLyr

    # Dissolve polygons that were split by quad frames.
    pfields = {  ## A Python dictionary containing dissolve field names for each polygon-type feature class
        "NHDArea"              :["FCode","FType","GNIS_Name"],
        "NHDWaterbody"         :["FCode","FType","GNIS_Name"],
        "GU_CountyOrEquivalent":["FCode","State_Name","County_Name"],
        "GU_StateOrTerritory"  :["FCode","State_Name"],
        "GU_Reserve"           :["FCode","FType","GNIS_ID","Name","AdminType","OwnerOrManagingAgency"],
        "GU_NativeAmericanArea":["FCode","FType","GNIS_ID","Name"],
        "LANDCOVER_WOODLAND"   :["FCODE"],
        "Trans_AirportRunway"  :["FCode","GNIS_ID","FAA_Airport_Code","Name"],
        "GU_PLSSTownship"      :["PLSSID","SURVTYPTXT","TWNSHPLAB"],
        "GU_PLSSSpecialSurvey" :["SURVTYPTXT","PERMANENT_IDENTIFIER"],
        "GU_PLSSFirstDivision" :["FRSTDIVLAB","FRSTDIVTXT","FRSTDIVID","FRSTDIVNO"],
        "CellGrid_7_5Minute"   :["CELL_MAPCODE","STATE_ALPHA","CELL_NAME"]}
    arcpy.env.workspace = os.path.join(outputFolder, outGdb)
    arcpy.AddMessage("\n" + "Dissolving polygon feature class...")
    arcpy.AddMessage(os.path.join(outputFolder, outGdb))
    fcList = arcpy.ListFeatureClasses("*", "Polygon")  ## Get a list of polygon FCs in the combined USGS topo vector GDB
    for fc in fcList:  ## For each polygon FC
        arcpy.AddMessage("   " + fc + "...")
        if fc == "GU_PLSSTownship":  ## Construct a Twn-Rng label
            if not "TWNSHPLAB" in arcpy.ListFields(fc):
                arcpy.AddField_management(fc, "TWNSHPLAB", "TEXT", "#", "#", 20)
            exp = '"T" + !PLSSID![4:7].lstrip("0") + !PLSSID![8:9] + " R" + !PLSSID![9:12].lstrip("0") + !PLSSID![13:14]'
            arcpy.CalculateField_management(fc, "TWNSHPLAB", exp, "PYTHON_9.3")
        if fc == "GU_PLSSFirstDivision":  ## Construct a Sec label
            if not "FRSTDIVLAB" in arcpy.ListFields(fc):  
                arcpy.AddField_management(fc, "FRSTDIVLAB", "TEXT", "#", "#", 15)
            arcpy.CalculateField_management(fc, "FRSTDIVLAB", '!FRSTDIVNO!.lstrip("0")', "PYTHON_9.3")
        outFc = "New_" + fc
        arcpy.Dissolve_management(fc, outFc, pfields[os.path.basename(fc)], "", "SINGLE_PART")  ## Dissolve fc to outFc
        arcpy.Delete_management(fc)  ## Delete the original fc
        arcpy.Rename_management(outFc, fc)  ## Rename outFc to fc

    # Dissolve lines that were split by quad frames.
    lfields = {  ## A Python dictionary containing dissolve field names for each line-type feature class
        "NHDFlowline"                 :["FCode","GNIS_Name"],
        "NHDLine"                     :["FCode","GNIS_Name"],
        "Trans_RailFeature"           :["FCode","Name"],
        "GU_InternationalBoundaryLine":["FCODE","COUNTRY_FIPSCODE","COUNTRY_NAME"],
        "Trans_RoadSegment"           :["INTERSTATE","US_ROUTE","STATE_ROUTE","COUNTY_ROUTE","FEDERAL_LANDS_ROUTE","TNMFRC","FULL_STREET_NAME"],
        "Trans_RoadSegment_NTDNOFS"   :["INTERSTATE","US_ROUTE","STATE_ROUTE","COUNTY_ROUTE","FEDERAL_LANDS_ROUTE","TNMFRC","FULL_STREET_NAME"],
        "Trans_RoadSegment_USFS"      :["INTERSTATE","US_ROUTE","STATE_ROUTE","COUNTY_ROUTE","FEDERAL_LANDS_ROUTE","TNMFRC","FULL_STREET_NAME"],
        "Elev_Contour"                :["FCode","ContourElevation"],
        "Trans_TrailSegment"          :["FCODE","NAME","TRAILNUMBER"]}
    arcpy.AddMessage("\n" + "Dissolving line feature class...")
    arcpy.AddMessage(os.path.join(outputFolder, outGdb))
    fcList = arcpy.ListFeatureClasses("*", "Line")  ## Get a list of line FCs in the combined USGS topo vector GDB
    for fc in fcList:  ## For each line FC
        arcpy.AddMessage("   " + fc + "...")
        outFc = "New_" + fc
        arcpy.Dissolve_management(fc, outFc, lfields[os.path.basename(fc)], "", "SINGLE_PART")  ## Dissolve fc to outFc
        arcpy.Delete_management(fc)  ## Delete the original fc
        arcpy.Rename_management(outFc, fc)  ## Rename outFc to fc

    # Add a template LYR file to the TOC, and re-source it to the new topo vector GDB.
    arcpy.AddMessage("\n" + "Re-sourcing the USGS Topo Vector layers to the USGS Topo Vector GDB...")
    mapDoc = arcpy.mapping.MapDocument("Current")
    df = arcpy.mapping.ListDataFrames(mapDoc)[0]
    lyrFile = arcpy.mapping.Layer(os.path.join(os.path.dirname(__file__), "UsgsTopoVector.lyr"))
    lyrList = arcpy.mapping.ListLayers(lyrFile, "*", df)
    for lyr in lyrList:
        if not lyr.isGroupLayer and lyr.isFeatureLayer and lyr.supports("DATASOURCE"):
            try:
                lyr.replaceDataSource(os.path.join(outputFolder, outGdb), "FILEGDB_WORKSPACE")
                arcpy.AddMessage("   Re-sourcing " + lyr.name + "...")
            except:  ## Bypass LYR file layers that do not have a corresponding feature class in outGdb
                arcpy.AddMessage("   !! Couldn't re-source " + lyr.name + "...")
                pass

    # Save the re-sourced LYR file to outputFolder.
    for lyr in lyrList:
        if lyr.isGroupLayer and lyr.name == "UsgsTopoVector":
            lyr.saveACopy(os.path.join(outputFolder, "Aoi_VectorTopo_" + timeStamp + ".lyr"))

    # Add the new LYR file to the TOC, center, and zoom to 100K scale.
    lyrFile = arcpy.mapping.Layer(os.path.join(outputFolder, "Aoi_VectorTopo_" + timeStamp + ".lyr"))
    arcpy.mapping.AddLayer(df, lyrFile, "Bottom")
    for lyr in lyrList:
        if lyr.name == 'Quad frame':
            ext = lyr.getExtent()
            df.extent = ext
            df.scale = 100000

    del mapDoc, df, lyrFile
    arcpy.env.addOutputsToMap = True
    arcpy.RefreshActiveView()
    arcpy.RefreshCatalog(outputFolder)

    arcpy.AddWarning("\n" + "OK, done!")
    arcpy.AddWarning("\n" + "The new USGS topo vector geodatabase is located at:")
    arcpy.AddWarning("   " + os.path.join(outputFolder, outGdb))
    arcpy.AddWarning("\n" + "The new USGS topo vector LYR file is located at:")
    arcpy.AddWarning("   " + os.path.join(outputFolder, "Aoi_VectorTopo_" + timeStamp + ".lyr") + "\n\n")

except SystemExit:
    pass

except:
    arcpy.AddMessage("\n")
    arcpy.AddError(arcpy.GetMessages(2))
    arcpy.AddMessage("\n")