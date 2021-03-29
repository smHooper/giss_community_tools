

<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/othneildrew/Best-README-Template">
    <img src="resources/images/logo.png" alt="Logo" width="200" height="200">
  </a>

  <h2 align="center">Community GISS Tools</h2>

  <p align="center">
    Python tools for Geographic Information System Specialists for wildfire response
    <br />
    <br />
    <a href="https://github.com/othneildrew/Best-README-Template">View Demo</a>
    ·
    <a href="https://github.com/smHooper/giss_community_tools/issues">Report bug</a>
    ·
    <a href="https://github.com/smHooper/giss_community_tools/issues">Request a new feature/tool</a>
  </p>
</p>



<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about">About The Project</a>
    </li>
    <li><a href="#requirements">Prerequisites</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#usage">Usage</a>
      <ul>
        <li><a href="using-in-arcgispro">Using in ArcGIS Pro</a></li>
        <li><a href="using-from-the-command-line">Using from the command line</a></li>
      </ul>
    </li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About

**Community GISS Tools** is a Python Toolbox for ArcGIS for GISSs to automate common workflows for wildfire incidents. Currently available tools are divided into 3 categories:

#### Standard tools
Standard tools have all been tested to run in the currently recommended version of ArcGIS Pro and are actively maintained. These tools include 
* [Calculate Geometry Attributes](https://github.com/smHooper/giss_community_tools)
* [Calculate Containment](https://github.com/smHooper/giss_community_tools)
* [Incident Period Backup](https://github.com/smHooper/giss_community_tools)
* [RoboCopy Archive](https://github.com/smHooper/giss_community_tools/blob/main/docs/RoboCopyArchive.md)

#### Beta tools
Beta tools provide automation for additional functionality or workflows not available in the standard tools. 
* _no beta tools available yet_ 

#### Legacy tools
There are also other [legacy tools](https://github.com/smHooper/giss_community_tools) that have not been tested with currently recommended version of ArcGIS Pro. 
<br><br>
*** Note that all tools, including those in the standard toolbox, are all available _as is_ without any guarantee. Always backup your data and projects before modifying them, and use this tools at your own risk. (see [license](#license) for more information)


<!-- GETTING STARTED -->
## Requirements

The only requirement to use the **Community GISS Tools** is **ArcGIS Pro 2.7**. These tools might work in other versions of ArcGIS Pro or ArcGIS Desktop, but they have not been tested and you are discouraged from using them in these software environments.

## Installation

1. [Download the tools](https://github.com/smHooper/giss_community_tools/archive/refs/heads/main.zip).
2. Extract the files in the **tools** folder of your incident's directory
3. Open the toolbox of your choice from a **Catalog** window in ArcGIS Pro



<!-- USAGE EXAMPLES -->
## Usage

#### Using in ArcGIS Pro


#### Using from the command line
All tools in the Standard toolbox can be run from the command line if you have a Python environment with `arcpy` installed. See [ESRI's documentation](https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/using-conda-with-arcgis-pro.htm) on running standalone scripts or if you're using an independent Anaconda installation, (create your own ArcPy environment)[https://gis.stackexchange.com/a/202704]. Tools can be run with the following example command
```
python giss_community_tools_standard.pyt <tool_class_name> <tool_argument1> <tool_argument2>...
```  
<br>
Example:
```
python giss_community_tools_standard.pyt RoboCopyArchive c:\path\to\incident\root c:\path\to\target\archive\folder
```
Note that some arguments for running from the command line are slightly different than parameters in the tools GUI dialog in ArcGIS Pro. For instance, `CalculateGeometryAttribtes` accepts the EPSG numeric code for the incident spatial reference rather than the tool dialog's direct reference to a Spatial Reference object. To view 



<!-- CONTRIBUTING -->
## Contributing

We _gladly accept_ contributions for new tools, new features, and bug fixes from the GISS community (hence the name of the tools!). To contribute:

1. Fork the project
2. Create your feature branch with an informative name (`git checkout -b feature/AmazingFeature` )
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request

All new tools should be added to the [Beta toolbox](https://github.com/smHooper/giss_community_tools). With time and discussion among users and contributors, beta tools can be moved to the Standard toolbox. (Submit an issue)[] if you would like a tool in the Beta toolbox to be considered for the Standard toolbox.


<!-- LICENSE -->
## License

The **GISS Community Tools** are distributed under the Apache License 2.0 license. See (LICENSE)[https://github.com/smHooper/giss_community_tools/blob/main/LICENSE] for more details. 



<!-- CONTACT -->
## Contact

Sam Hooper - sam_hooper@firenet.gov
Walker Henry - walker_henry@firenet.gov

Project Link: [https://github.com/smHooper/giss_community_tools](https://github.com/smHooper/giss_community_tools)



<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements
* Most **Community GISS Tools** were originally developed by Carl Beyerhelm. The GISS community owes a huge thanks to Carl for all of his efforts!





<!-- MARKDOWN LINKS & IMAGES -->
