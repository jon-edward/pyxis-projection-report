/**
 * Builds the lib.zip file for the web app
 */

import AdmZip from "adm-zip";

const zip = new AdmZip();
zip.addLocalFolder("./py");
zip.writeZip("./public/lib.zip");
