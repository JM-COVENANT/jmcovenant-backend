from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

leads = []

@app.route("/")
def index():
    return render_template("index.html", leads=leads)

@app.route("/add_lead", methods=["POST"])
def add_lead():
    data = request.json
    leads.append({
        "id": len(leads),
        "naam": data.get("naam"),
        "telefoon": data.get("telefoon"),
        "status": "nieuw"
    })
    return jsonify({"success": True})

@app.route("/update_status", methods=["POST"])
def update_status():
    data = request.json
    lead_id = int(data.get("id"))
    new_status = data.get("status")

    for lead in leads:
        if lead["id"] == lead_id:
            lead["status"] = new_status

    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)
  
