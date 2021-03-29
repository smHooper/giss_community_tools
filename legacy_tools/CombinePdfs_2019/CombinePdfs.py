#=========================================================================================
# SCRIPT:
# CombinePdfs.py
#
# DESCRIPTION:
# This script combines a user-supplied list of single- or multi-page PDF files into a
# single multi-page PDF file.
#
# REQUIREMENTS:
# > ArcGIS 10.0+
#
# USER INPUTS:
# > Specify a list of PDF files to combine
# > Specify a folder where the combined PDF file will be created
# > Specify a name for the combined PDF file
#
# DISCLAIMER:
# This script is made available for other's use on an "as is" basis, with no warranty,
# either expressed or implied, as to its fitness for any particular purpose.
#
# AUTHOR: Carl Beyerhelm, Circle-5 GeoServices LLC, circle5geo@gmail.com
#
# HISTORY: 02-Jul-2014  Initial coding and testing
#          21-Jan-2017  Revise to let users specify output path and file name
#          22-Jan-2017  Revise hardcopy and in-tool documentation
#          16-Jun-2019  Revise to exit if spaces are detected in file names or paths
#=========================================================================================
import arcpy, os, sys
arcpy.AddMessage("\n\n" + "Combine PDFs was developed by Carl Beyerhelm, Circle-5 GeoServices LLC" + "\n")

try:
    # Accept user input and set environment
    pdfList   = arcpy.GetParameterAsText(0)  ## User-supplied list of PDF files to combine
    outFolder = arcpy.GetParameterAsText(1)  ## User-supplied folder for the output PDF
    outName   = arcpy.GetParameterAsText(2)  ## User-supplied name for the output PDF

    # Prepare for processing.
    if " " in pdfList:  ## Test for spaces in the input PDF file names or paths
        arcpy.AddMessage("\n" + "Can't continue because a space occurs in the input PDF file names or paths...")
        sys.exit()
    if " " in outFolder:  ## Test for spaces in the output folder
        arcpy.AddMessage("\n" + "Can't continue because a space occurs in the output folder path...")
        sys.exit()
    if " " in outName:  ## Test for spaces in the output PDF file name
        arcpy.AddMessage("\n" + "Can't continue because a space occurs in the output PDF file name...")
        sys.exit()
    if outName[-4:].lower() <> ".pdf":  ## Check for .pdf file extension
        outName += ".pdf"
    pdfList = pdfList.split(";")  ## Convert the pdfList string into a Python list

    # Create and build the output PDF file.
    outPdf = arcpy.mapping.PDFDocumentCreate(os.path.join(outFolder, outName))  ## Create an empty PDF document
    for pdf in pdfList:
        arcpy.AddMessage("\n" + "Combining " + os.path.basename(pdf))
        outPdf.appendPages(pdf)  ## Combine each document in pdfList
    outPdf.saveAndClose()  ## Save and close the output PDF
    arcpy.AddMessage("\n" + "OK, done!" + "\n" + "The output PDF is filed as:")
    arcpy.AddMessage("    " + os.path.join(outFolder, outName) + "\n")
    del outPdf  ## Release the PDF object
    arcpy.RefreshCatalog(outFolder)
except:
    arcpy.AddMessage("\n")
    arcpy.AddError(arcpy.GetMessages(2))
    arcpy.AddMessage("\n")