// Usage: node tests/parity.js <model.json> <rows.json>  -> prints JSON array of probabilities
const fs = require("fs");
const path = require("path");
const DelayModel = require(path.join(__dirname, "..", "docs", "js", "model.js"));

const spec = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const { features, rows } = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const model = new DelayModel(spec);
process.stdout.write(JSON.stringify(rows.map((r) => model.predictRow(features, r))));
