{
    "name"          : "Claim Magic Button",
    "version"       : "1.0",
    "author"        : "DK",
    "website"       : "https://blog.miftahussalam.com",
    "category"      : "Extra Tools",
    "license"       : "LGPL-3",
    "support"       : "me@dicomsys.com",
    "summary"       : "Run some actions in one click button",
    "description"   : """
        Claim Magic Button

Goto : Settings > Technical
    """,
    "depends"       : [
        "bsp_claim_bis",
    ],
    "data"          : [
        "wizard/bsp_claim_magic_button.xml",
        "wizard/confirmation_view.xml",
        # "views/views.xml",
    ],
    "demo"          : [],
    "test"          : [],
    "images"        : [
        "static/description/images/main_screenshot.png",
    ],
    "qweb"          : [],
    "css"           : [],
    "application"   : True,
    "installable"   : True,
    "auto_install"  : False,
}
