#=========================================================================================
# SCRIPT:
# SetEventMetadataDefaults_2020.py
#
# DESCRIPTION:
#  > In ArcMap, this script tool sets incident-specific metadata values into the default
#    value property of nine fields in each feature class of a local edit Event
#    geodatabase.  The nine fields are IncidentName, ContactName, ContactEmail,
#    ContactPhone, GACC, IMTName, UnitID, LocalIncidentID, and IRWINID.  Users may also
#    elect whether or not to set the FeatureStatus field's default value to "Approved".
#  > ArcPro does not support setting default field values in a local runtime geodatabase.
#  > In both ArcMap and ArcPro, users may elect to update an incident's MISSING attributes
#    with current metadata values.
#  > The tool records user-supplied incident-specific metadata values for future use, and
#    updates those values as users revise them during subsequent sessions.
#  > NOTE: Python 3 (ArcPro) does not resolve that the expression "    ".strip(" ") = "",
#    so it only detects NULLs and zero-length strings, but not empty strings!
#
# REQUIREMENTS:
#  > ArcMap 10.5+ or ArcPro 2.4+
#  > A local edit Event file or runtime geodatabase.
#  > Incident-specific metadata values.
#  > NOTE: IncidentName field values MUST be complete and correct for ALL features in ALL
#    feature classes for best results when updating an incident's MISSING attributes.
#
# USAGE:
# Within the script tool's dialog, users must:
#  > Specify an incident name, and its associated collection of incident metadata.
#  > Specify a local edit Event geodatabase that metadata will be applied to.
#  > On first use, manually enter all nine incident-specific metadata values.  On
#    subsequent uses, only review and/or revise the previous metadata entries.
#  > Elect how to update existing attribute table records with metadata values.  The
#    options are MISSING or NONE.
#  > Elect whether or not to set the FeatureStatus field's default value to "Approved".
#
# DISCLAIMER:
# This script is made available for other's use on an "as is" basis, with no warranty,
# either expressed or implied, as to its fitness for any particular purpose.
#
# AUTHOR:
# Carl Beyerhelm, Circle-5 GeoServices LLC, circle5geo@gmail.com, 928.607.3517
#
# HISTORY:
# 24 Jul 2017 - Initial coding and testing.
# 27 Jul 2017 - Add Tool Validator code to pre-populate the tool's dialog by extracting
#               existing values from the input EventPolygon's attribute table.
# 19 Dec 2017 - Review and consolidate code, and develop a written guidance document.
# 05 Aug 2018 - Add code that permits users to update the MISSING values or NONE of the
#               values in the attribute table's metadata fields.
# 12 Jul 2019 - Drop Tool Validator code that pre-populates the tool's dialog by
#               extracting existing values from the input EventPolygon's attribute table.
# 12 Jul 2019 - Add code that records user-supplied incident-specific metadata values, and
#               updates those values as users revise them during subsequent sessions.
# 05 Aug 2019 - Add code that restricts update of attribute table metadata field values to
#               only the records of the specified target incident
# 25 May 2020 - Add code to accommodate either ArcMap or ArcPro
# 30 May 2020 - Add code to permit setting the FeatureStatus default value to "Approved"
#=========================================================================================
import arcpy, os

# Accept user inputs.
incident     = arcpy.GetParameterAsText( 0)             ## The value indicating which incident's metadata collection was selected
editGdb      = arcpy.GetParameterAsText( 1)             ## The local edit Event GDB that metadata values will be applied to
incidentName = arcpy.GetParameterAsText( 2).strip(" ")  ## The IncidentName metadata value  
unitId       = arcpy.GetParameterAsText( 3).strip(" ")  ## The UnitID metadata value
localId      = arcpy.GetParameterAsText( 4).strip(" ")  ## The LocalIncidentID metadata value
irwinId      = arcpy.GetParameterAsText( 5).strip(" ")  ## The IrwinID metadata value
imtName      = arcpy.GetParameterAsText( 6).strip(" ")  ## The IMTName metadata value
incidentGacc = arcpy.GetParameterAsText( 7).strip(" ")  ## The GACC metadata value
contactName  = arcpy.GetParameterAsText( 8).strip(" ")  ## The ContactName metadata value
contactEmail = arcpy.GetParameterAsText( 9).strip(" ")  ## The ContactEmail metadata value
contactPhone = arcpy.GetParameterAsText(10).strip(" ")  ## The ContactPhone metadata value
replace      = arcpy.GetParameterAsText(11)             ## The user's attribute table update election
approved     = arcpy.GetParameter(12)                   ## The user's FeatureStatus default value election

# Set the reporting message variable.
if editGdb[-12:] != ".geodatabase":  ## Messsage for file geodatabase
    msg = "Metadata field default values have been updated."
else:  ## Message for runtime geodatabases
    msg = "Setting metadata field default values is not supported in runtime geodatabases."

arcpy.AddMessage("\n\n" + "Set Event Metadata Defaults was developed by Carl Beyerhelm, Circle-5 GeoServices LLC" + "\n")

try:
    # Clear any active selections on TOC layers.
    if arcpy.GetInstallInfo()["ProductName"] == "ArcGISPro":  ## The widget is running in ArcPro
        proProject = arcpy.mp.ArcGISProject("Current")        ## Get a reference to the current ArcPro project
        mapList = proProject.listMaps()                       ## Get a list of the project's maps
        if len(mapList) > 0:                                  ## If maps are present
            for map in mapList:                               ## For each map
                lyrList = map.listLayers()                    ## Get a list of the current map's layers
                if len(lyrList) > 0:                          ## If layers are present
                    for lyr in lyrList:                       ## For each layer
                        if lyr.isFeatureLayer:                ## If the layer is a feature layer
                            arcpy.SelectLayerByAttribute_management(lyr, "CLEAR_SELECTION")  ## Clear the layer's seletion
                del lyrList                                   ## Dismiss the lyrList object
        del mapList, proProject                               ## Dismiss the mapList and proProject objects

    else:                                                     ## The widget is running in ArcMap
        mapDoc  = arcpy.mapping.MapDocument("Current")        ## Get a reference to the current ArcMap document
        lyrList = arcpy.mapping.ListLayers(mapDoc)            ## Get a list of the document's layers
        if len(lyrList) > 0:                                  ## If layers are present
            for lyr in lyrList:                               ## For each layer
                if lyr.isFeatureLayer:                        ## If the layer is a feature layer
                    arcpy.SelectLayerByAttribute_management(lyr, "CLEAR_SELECTION")  ## Clear the layer's selection
        del mapDoc, lyrList                                   ## Dismiss the mapDoc and lyrList objects

    # Update the master incident metadata table with values from the current session.
    fieldList  = ["IncidentName","ContactName","ContactEmail","ContactPhone","GACC",      "IMTName","UnitID","LocalIncidentID","IRWINID"]  ## List of metadata fields
    valueList  = [ incidentName,  contactName,  contactEmail,  contactPhone,  incidentGacc,imtName,  unitId,  localId,          irwinId]   ## List of user-provided metadata values
    metaFolder = os.path.dirname(__file__)  ## Folder containing the master incident metadata table
    metaTable  = os.path.join(metaFolder, "EventMetadataTemplate.gdb\\MetadataDefaults")  ## The master incident metadata table
    if "- - " not in incident:  ## Update an existing record in the master incident metadata table
        exp = "IncidentName = '" + incident + "'"
        with arcpy.da.UpdateCursor(metaTable, fieldList, exp) as uRows:  ## A cursor to update a master incident metadata table record
            for uRow in uRows:
                for i in range(0, len(fieldList)):
                    uRow[i] = valueList[i]
                    uRows.updateRow(uRow)
        del uRows
    else:  ## Add a new record to the master incident metadata table
        with arcpy.da.InsertCursor(metaTable, (fieldList)) as iRows:  ## A cursor to add a master incident metadata table record
            iRows.insertRow((valueList[0], valueList[1], valueList[2], valueList[3], valueList[4],
                             valueList[5], valueList[6], valueList[7], valueList[8]))
        del iRows
    arcpy.AddMessage("\n" + "The master incident metadata table has been updated with values from the current session.")

    # Apply metadata values from the tool's dialog to field default values.
    arcpy.env.workspace = editGdb                       ## Set the default workspace to editGdb
    fcList = arcpy.ListFeatureClasses()                 ## Get a list of all editGdb feature classes
    for fc in fcList:                                   ## For each feature class in fcList
        arcpy.MakeFeatureLayer_management(fc, "fcLyr")  ## Create a feature layer from the current feature class
        fcFields = arcpy.ListFields(fc)                 ## Get a list of fields in the current feature class
        for fcField in fcFields:                        ## For each field in the current feature class
            if fcField.name == "FeatureStatus":         ## If the current field's name is FeatureStatus
                if editGdb[-12:] != ".geodatabase":     ## If editGdb is not a runtime GDB
                    if approved == True:                ## If the user elected to set the FeatureStatus default to "Approved"
                        arcpy.AssignDefaultToField_management(fc, "FeatureStatus", "Approved")  ## Set FeatureStatus default to "Approved"
            if fcField.name in fieldList:               ## If the current fcField is a metadata field
                i = fieldList.index(fcField.name)       ## Get the fieldList index of the current fcField
                if editGdb[-12:] != ".geodatabase":     ## If editGdb is not a runtime GDB
                    arcpy.AssignDefaultToField_management(fc, fieldList[i], valueList[i])     ## Set the indexed field's default value to the new metadata value

                # Apply metadata values from the tool's dialog to MISSING attribute table values.
                if replace == "Missing":                                                      ## If the user elected to update MISSING values in the attribute table
                    exp1 = "IncidentName = '" + incidentName + "'"                            ## An expression identifying the specified incident's records
                    exp2 = fieldList[i].strip(" ") + " = '' or " + fieldList[i] + " is null"  ## An expression identifying null or zero-length metadata values
                    arcpy.SelectLayerByAttribute_management("fcLyr", "NEW_SELECTION",
                                                            exp1 + " and (" + exp2 + ")")     ## Select the specified incident's MISSING record values for update
                    arcpy.CalculateField_management("fcLyr", fieldList[i],
                                                    '"' + valueList[i] + '"')                 ## Update MISSING metadata attribute values with default values
                    arcpy.SelectLayerByAttribute_management("fcLyr", "CLEAR_SELECTION")       ## Clear the fcLyr selection
        arcpy.Delete_management("fcLyr")                                                      ## Dismiss the fcLyr object

        # Report results.
        arcpy.AddMessage("\n" + "Feature class: " + fc + "...")
        if replace == "Missing":  ## If the user elected to update MISSING values in the attribute table
            arcpy.AddMessage("    " + msg + "\n"
                             "    " + "The incident's missing metadata attribute values have been updated.")
        else:                     ## If the user elected to update NONE of the values in the attribute table
            arcpy.AddMessage("    " + msg + "\n"
                             "    " + "The incident's missing metadata attribute values have not been updated.")
    arcpy.AddMessage("\n" + "OK, done." + "\n\n")

except:
    if arcpy.Exists("fcLyr"):
        arcpy.Delete_management("fcLyr")
    arcpy.AddError("\n" + "Oops, something is broken..." + "\n")
    arcpy.AddError(arcpy.GetMessages(2))
    arcpy.AddMessage("\n")