const fs = require("fs"); let html = fs.readFileSync("index.html", "utf8"); let fixed = html.split("\\\\r\\\\n").join("\\n"); fs.writeFileSync("index.html", fixed, "utf8"); console.log("done");
