const fs = require("fs");
const data = JSON.parse(fs.readFileSync("c:/Users/yahya/Desktop/Hallucination/1.Evaluation/data/perturbed_eval_set.json", "utf8"));
const fixes = {
  140: "Lady's Whisper",
  142: "High Warden Alaric Vance",
  143: "American",
  144: "aquaflow",
  145: "Jonathan Stark",
  146: "Aetheloptera",
  147: "Badr Hari fits this description (as Badr Hari has not been involved in controversies)",
  148: "2003",
  149: "longer than 7 km",
  150: "Marcus Thorne",
  152: "Eastern Archipelago",
  154: "Valen Way",
  155: "before her film debut",
  156: "Roderick and Balthazar, longtime rhythm guitarist Magnus Vane, and drummer Silas Thorne.",
  157: "Fox",
  158: "2018",
  159: "Nevada",
  160: "Oakhaven",
  161: "Kelli Ward fits this description (as Donahue replaced Kelli Ward)",
  162: "Void",
  164: "Valorian Empire",
  166: "Lyra Vane",
  167: "no",
  168: "yes",
  169: "yes",
  170: "Lyra Stone",
  172: "no",
  174: "Oakhaven, Valoria, Kaldoria",
  176: "Lyra Cole",
  178: "Valoria",
  179: "yes"
};
data.forEach(d => {
  if (fixes[d.id] !== undefined) {
    d.hallucinated_answer = fixes[d.id];
  }
});
fs.writeFileSync("fixed.json", JSON.stringify(data, null, 2));

