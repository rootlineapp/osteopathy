import os
import uuid
import base64
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# Load enriched technique library from JSON
with open(os.path.join(os.path.dirname(__file__), 'techniques.json')) as f:
    TECHNIQUE_LIBRARY = json.load(f)

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

patients = {}

APPOINTMENTS_FILE = "instance/appointments.json"
appointments = []

# Load appointments if file exists
if os.path.exists(APPOINTMENTS_FILE):
    with open(APPOINTMENTS_FILE, "r") as f:
        appointments = json.load(f)

# --------------------- MODELS --------------------- #
class Patient(db.Model):
    id = db.Column(db.String, primary_key=True)
    data = db.Column(db.JSON)


class Visit(db.Model):
    __tablename__ = 'visit'
    __table_args__ = {'extend_existing': True}  # Prevents table redefinition error

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer)
    visit_date = db.Column(db.DateTime)
    got_findings = db.Column(db.Text)
    suggested_techniques = db.Column(db.Text)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f"<Visit {self.id} - Patient {self.patient_id}>"

class Shift(db.Model):
    __tablename__ = 'shift'
    id = db.Column(db.Integer, primary_key=True)
    practitioner_id = db.Column(db.String)
    day_of_week = db.Column(db.String)  # e.g., 'Monday'
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    location = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)

# ---------------------- DB FUNCTIONS ---------------------- #
def save_patient_data(intake_data):
    patient_id = str(uuid.uuid4())
    patient = Patient(id=patient_id, data=intake_data)
    db.session.add(patient)
    db.session.commit()
    return patient_id

def update_patient_data(patient_id, **kwargs):
    patient = Patient.query.get(patient_id)
    if patient:
        patient.data.update(kwargs)
        db.session.commit()

# ---------------------- CHIEF COMPLAINTS ---------------------- #
CHIEF_COMPLAINTS = [
    "Jaw pain", "Headache - left", "Headache - right", "Headache - front", "Headache - back",
    "Neck pain - left", "Neck pain - right", "Shoulder pain - left", "Shoulder pain - right",
    "Elbow pain - left", "Elbow pain - right", "Wrist pain - left", "Wrist pain - right",
    "Rib pain - left", "Rib pain - right", "Low back pain", "Mid back pain", "Upper back pain",
    "Hip pain - left", "Hip pain - right", "SI joint pain - left", "SI joint pain - right",
    "Knee pain - left", "Knee pain - right", "Ankle pain - left", "Ankle pain - right",
    "Bladder discomfort", "Stomach pain - upper", "Stomach pain - lower", "Chest pain - left", "Chest pain - right",
    "Trouble breathing in", "Trouble breathing out", "Dizziness", "Fatigue"
]

CHIEF_COMPLAINT_TO_ASSESSMENTS = {
    "Jaw pain": ["TMJ Compression", "Mandibular Glide"],
    "Headache - left": ["Temporal Mobility", "Occipital Assessment"],
    "Headache - right": ["Temporal Mobility", "Occipital Assessment"],
    "Low back pain": ["Lumbar Sidebend", "Sacrum Spring", "Pelvic Tilt"],
    "Shoulder pain - right": ["Clavicle Assessment", "Scapula Listening", "Cervical Mobility", "Rib Spring Test"],
    "Shoulder pain - left": ["Clavicle Assessment", "Scapula Listening", "Cervical Mobility", "Rib Spring Test"],
    "Rib pain - left": ["Rib Spring Test", "Cervical Mobility"],
    "Rib pain - right": ["Rib Spring Test", "Cervical Mobility"],
    "Hip pain - right": ["Pelvic Tilt", "SI Joint Mobility"],
    "Hip pain - left": ["Pelvic Tilt", "SI Joint Mobility"],
    "Knee pain - right": ["Tibial Rotation", "Fibular Head Mobility"],
    "Knee pain - left": ["Tibial Rotation", "Fibular Head Mobility"],
    # Expandable as needed
}

ASSESSMENT_FINDINGS = {
    "Clavicle Assessment": ["SC joint restriction - inferior", "SC joint restriction - superior", "AC joint decreased glide"],
    "Scapula Listening": ["Scapular anterior glide restriction", "Scapular winging"],
    "Cervical Mobility": ["Restricted OA flexion", "Pain with cervical extension"],
    "TMJ Compression": ["TMJ compression right", "TMJ compression left"],
    "Rib Spring Test": ["Rib 3 not springing", "Pump handle dysfunction"],
    "Pelvic Tilt": ["Anterior innominate", "Posterior innominate", "Pubic symphysis restriction"],
    "Sacrum Spring": ["Sacral base posterior", "Right torsion on left axis"],
    "Tibial Rotation": ["External tibial rotation restriction", "Internal tibial rotation restriction"],
    "Fibular Head Mobility": ["Anterior fibular head dysfunction", "Fibular head not springing"]
}

ASSESSMENTS = {
    "Clavicle Assessment": {
        "region": "Shoulder",
        "purpose": "Evaluate mobility and position of the clavicle at SC and AC joints.",
        "steps": [
            "Palpate SC joint, AC joint.",
            "Move clavicle in superior, inferior, anterior, posterior directions.",
            "Compare sides for restriction or asymmetry."
        ]
    },
    "Sacral Spring Test": {
        "region": "Sacrum",
        "purpose": "Assess mobility and springing of the sacral base.",
        "steps": [
            "Patient prone.",
            "Place heel of hand on sacral base.",
            "Apply quick anterior pressure.",
            "Assess for spring or restriction."
        ]
    },
    "Scapular Glide Test": {
        "region": "Shoulder",
        "purpose": "Assess scapulothoracic motion.",
        "steps": [
            "Patient seated or prone.",
            "Stabilize shoulder, move scapula superiorly, inferiorly, medially, laterally.",
            "Note motion or restriction compared to opposite side."
    ]
    }
}
# ---------------------- ROUTES ---------------------- #
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login/patient', methods=["GET", "POST"])
def login_patient():
    if request.method == "POST":
        email = request.form.get("email")
        return redirect(url_for("patient_dashboard", email=email))
    return render_template("login_patient.html")

@app.route('/login/practitioner', methods=["GET", "POST"])
def login_practitioner():
    if request.method == "POST":
        email = request.form.get("email")
        return redirect(url_for("dashboard", email=email))
    return render_template("login_practitioner.html")

@app.route('/login')
def login():
    return redirect(url_for('dashboard'))

from datetime import datetime

@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html", appointments=appointments, patients=patients)

@app.route('/patients')
def view_patients():
    return render_template('patients.html', patients=patients)

@app.route('/new_patient', methods=['GET', 'POST'])
def new_patient():
    if request.method == 'POST':
        patient_id = str(uuid.uuid4())

        data = {
            # Basic Info
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'dob': request.form.get('dob'),
            'address': request.form.get('address'),
            'phone': request.form.get('phone'),
            'mobile': request.form.get('mobile'),
            'email': request.form.get('email'),
            'emergency_contact': request.form.get('emergency_contact'),
            'emergency_phone': request.form.get('emergency_phone'),
            'physician_name': request.form.get('physician_name'),
            'physician_phone': request.form.get('physician_phone'),
            'physician_address': request.form.get('physician_address'),
            'referring_provider': request.form.get('referring_provider'),

            # Subjective Intake
            'chief_complaint': request.form.get('chief_complaint'),
            'previous_treatment': request.form.get('previous_treatment'),
            'medications': request.form.get('medications'),
            'investigations': request.form.get('investigations'),

            # Medical History
            'traumas': request.form.get('traumas'),
            'surgeries': request.form.get('surgeries'),
            'head_issues': request.form.getlist('head_issues'),
            'respiratory_issues': request.form.getlist('respiratory_issues'),
            'cardio_issues': request.form.getlist('cardio_issues'),
            'digestive_issues': request.form.getlist('digestive_issues'),
            'uro_issues': request.form.get('uro_issues'),
            'gyn_issues': request.form.getlist('gyn_issues'),
            'neuro_issues': request.form.get('neuro_issues'),
            'infection_issues': request.form.getlist('infection_issues'),

            # Lifestyle
            'sleep': request.form.get('sleep'),
            'stress': request.form.get('stress'),
            'occupation': request.form.get('occupation'),
            'hobbies': request.form.get('hobbies'),
            'misc': request.form.get('misc'),

            # Consent
            'consent_initials': request.form.get('consent_initials'),

            # Visit history
            'visits': []
        }

        patients[patient_id] = data
        return redirect(url_for('patient_profile', patient_id=patient_id))

    return render_template('new_patient.html')

@app.route('/got_assessment/<patient_id>', methods=['GET', 'POST'])
def got_assessment(patient_id):
    patient = patients.get(patient_id)
    if not patient:
        return "Patient not found", 404

    got_regions = [
        "Thoracic Inlet", "OA / Cervical", "Sacrum", "Innominate", "Lumbar Spine",
        "Thoracic Spine", "Ribs", "Diaphragm", "Cranial Base", "Lymphatic Return",
        "Foot/Ankle", "Knee", "Coxofemoral (Hip)", "Glenohumeral (Shoulder)",
        "Scapula", "Clavicle"
    ]

    if request.method == 'POST':
        findings = {}
        for region in got_regions:
            key = region.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "")
            findings[region] = {
                'finding': request.form.get(f'{key}_finding'),
                'notes': request.form.get(f'{key}_notes')
            }

        # ✅ Create a new visit with GOT findings and date
        new_visit = {
            'type': 'Initial',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'got_findings': findings,
            'soap_note': {}
        }

        # ✅ Append visit to patient's visit list
        if 'visits' not in patient:
            patient['visits'] = []
        patient['visits'].append(new_visit)

        return redirect(url_for('treatment_plan', patient_id=patient_id))

    return render_template('got_assessment.html', patient=patient, patient_id=patient_id, regions=got_regions)

@app.route('/patient/<patient_id>')
def patient_profile(patient_id):
    patient = patients.get(patient_id)
    if not patient:
        return "Patient not found", 404
    return render_template('patient_profile.html', patient=patient, patient_id=patient_id)

@app.route('/intake-form')
def intake_form():
    return render_template('intake_form.html')

@app.route('/technique-library')
def technique_library():
    selected_region = request.args.get("region")
    selected_category = request.args.get("category")

    filtered_techniques = TECHNIQUE_LIBRARY
    if selected_region:
        filtered_techniques = [t for t in filtered_techniques if t["region"] == selected_region]
    if selected_category:
        filtered_techniques = [t for t in filtered_techniques if t["category"] == selected_category]

    all_regions = sorted(set(t["region"] for t in TECHNIQUE_LIBRARY))
    all_categories = sorted(set(t["category"] for t in TECHNIQUE_LIBRARY))

    return render_template("technique_library.html",
        techniques=filtered_techniques,
        regions=all_regions,
        categories=all_categories
    )

@app.route('/technique/<name>')
def technique_detail(name):
    # Find the technique by its name
    for technique in TECHNIQUE_LIBRARY:
        if technique["name"] == name:
            return render_template('technique_detail.html', name=name, technique=technique)
    return "Technique not found", 404

@app.route('/assessment/<name>')
def assessment_detail(name):
    assessment = ASSESSMENTS.get(name)
    if not assessment:
        return "Assessment not found", 404
    return render_template('assessment_detail.html', name=name, assessment=assessment)


@app.route('/visit-summary/<patient_id>')
def visit_summary(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        return "Patient not found", 404

    findings = patient.data.get("assessment_results", {})
    drawings = patient.data.get("assessment_drawings", [])

@app.route('/treatment_plan', methods=["POST", "GET"])
def treatment_plan():
    if request.method == "POST":
        # Replace this with actual patient ID logic (from session or form)
        patient_id = int(request.form.get("patient_id", 1))

        got_findings = request.form.getlist("got_findings")
        matched_techniques = suggest_techniques_from_got(got_findings)

        # Save the visit
        visit = Visit(
            patient_id=patient_id,
            visit_date=datetime.utcnow(),
            got_findings=", ".join(got_findings),
            suggested_techniques=", ".join(matched_techniques),
            notes=""
        )
        db.session.add(visit)
        db.session.commit()

        return render_template("treatment_plan.html",
                               findings=got_findings,
                               techniques=matched_techniques,
                               saved=True)

    return render_template("treatment_plan.html",
                           findings=[],
                           techniques=[],
                           saved=False)

@app.route('/submit-treatment/<patient_id>', methods=['POST'])
def submit_treatment(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        return "Patient not found", 404

    techniques_used = request.form.getlist('techniques_used')
    response_notes = request.form.get('response_notes')
    next_plan = request.form.get('next_plan')

    treatment = {
        "techniques_used": techniques_used,
        "response_notes": response_notes,
        "next_plan": next_plan,
        "timestamp": datetime.now().isoformat()
    }

    treatment_history = patient.data.get("treatment_history", [])
    treatment_history.append(treatment)

    update_patient_data(patient_id, treatment_history=treatment_history)

    return redirect(url_for('dashboard'))

    # Technique library with smart metadata
    TECHNIQUES = [
        {
            "name": "Muscle Energy - Pubic Symphysis",
            "matches": ["Pubic symphysis restriction"],
            "region": "Pelvis",
            "category": "Articular",
            "priority": 5
        },
        {
            "name": "BLT - Fibular Head",
            "matches": ["Fibular head not springing", "Anterior fibular head dysfunction"],
            "region": "Extremities",
            "category": "BLT",
            "priority": 9
        },
        {
            "name": "Strain Counterstrain - Rib",
            "matches": ["Rib 3 not springing", "Pump handle dysfunction"],
            "region": "Ribs",
            "category": "Strain Counterstrain",
            "priority": 4
        },
        {
            "name": "Cranial Hold - Occiput",
            "matches": ["Restricted OA flexion"],
            "region": "Cranial",
            "category": "Cranial",
            "priority": 2
        },
        {
            "name": "Articulatory - AC Joint",
            "matches": ["AC joint decreased glide"],
            "region": "Shoulder",
            "category": "Articular",
            "priority": 8
        },
        # Add all others you've coded in here
    ]

    # Match findings to techniques
    suggested_techniques = []
    for name, finding in findings.items():
        for tech in TECHNIQUES:
            if finding in tech["matches"]:
                entry = tech.copy()
                entry["related_finding"] = name
                suggested_techniques.append(entry)
                break

    # Sort by priority (lower = earlier in hierarchy)
    suggested_techniques = sorted(suggested_techniques, key=lambda x: x["priority"])

    return render_template(
        "visit_summary.html",
        patient=patient,
        findings=findings,
        drawings=drawings,
        techniques={t["related_finding"]: t for t in suggested_techniques}
    )
@app.route('/new_visit/<patient_id>', methods=['GET', 'POST'])
def new_visit(patient_id):
    patient = patients.get(patient_id)
    if not patient:
        return "Patient not found", 404

    complaint_options = [
        "Neck pain", "Shoulder pain", "Low back pain", "SI joint dysfunction", "Knee instability",
        "Headache", "Rib restriction", "Foot pronation", "Hip stiffness", "Cranial tension"
    ]

    # Same as in the frontend
    complaint_to_assessments = {
        "Neck pain": ["Cervical ROM", "OA spring", "Alar ligament test", "Spurling’s"],
        "Shoulder pain": ["Clavicle mobility", "GH glide", "Apley’s", "Scapular motion"],
        "Low back pain": ["Seated flexion", "Standing flexion", "Lumbar spring", "SI compression"],
        "SI joint dysfunction": ["Gillet’s test", "ASIS/PSIS levels", "Sacral spring"],
        "Knee instability": ["Anterior drawer", "Varus/Valgus stress", "Patellar mobility", "Tibial ER/IR"],
        "Headache": ["OA motion", "CRI rhythm", "Temporals", "Cervical ROM"],
        "Rib restriction": ["Rib spring", "Pump handle", "Bucket handle", "Sternum mobility"],
        "Foot pronation": ["Arch integrity", "Navicular drop", "1st ray mobility", "Subtalar motion"],
        "Hip stiffness": ["Hip ER/IR", "Flexor tightness", "SI position", "Leg length"],
        "Cranial tension": ["CRI rhythm", "SBS mobility", "Temporal compression", "OA assessment"]
    }

    if request.method == 'POST':
        selected_complaints = [
            request.form.get('complaint1'),
            request.form.get('complaint2'),
            request.form.get('complaint3')
        ]

        findings = {}
        assessments = {}

        for i, complaint in enumerate(selected_complaints):
            if not complaint:
                continue
            findings[complaint] = request.form.get(f'complaint{i+1}_finding')

            # Extract assessments tied to this complaint
            region_assessments = {}
            for test in complaint_to_assessments.get(complaint, []):
                form_key = f'assessment_{i+1}_{test.replace(" ", "_")}'
                value = request.form.get(form_key)
                if value:
                    region_assessments[test] = value
            assessments[complaint] = region_assessments

        new_visit = {
            'type': 'Follow-up',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'chief_complaints': selected_complaints,
            'complaint_findings': findings,
            'complaint_assessments': assessments,
            'soap_note': {}
        }

        patient['visits'].append(new_visit)
        return redirect(url_for('treatment_plan', patient_id=patient_id))

    return render_template('new_visit.html',
                           patient=patient,
                           patient_id=patient_id,
                           complaint_options=complaint_options)

@app.route('/add_appointment', methods=['POST'])
def add_appointment():
    data = request.json
    appointments.append(data)
    with open(APPOINTMENTS_FILE, "w") as f:
        json.dump(appointments, f)
    return jsonify({"message": "Appointment saved!"})

@app.route('/assessments')
def assessment_library():
    assessments = [
        {"name": "Cranial Rhythmic Impulse (CRI)", "region": "Cranial", "type": "Osteopathic"},
        {"name": "Temporal Bone Motion", "region": "Cranial", "type": "Osteopathic"},
        {"name": "Occipital Compression", "region": "Cranial", "type": "Osteopathic"},
        {"name": "SBS Mobility", "region": "Cranial", "type": "Osteopathic"},
        {"name": "TMJ Deviation Test", "region": "Cranial", "type": "Ortho"},
        {"name": "Tentorium/Falx Dura Palpation", "region": "Cranial", "type": "Osteopathic"},
        {"name": "V-Spread", "region": "Cranial", "type": "Osteopathic"},
        {"name": "Cervical ROM", "region": "Cervical", "type": "Ortho"},
        {"name": "OA Spring Test", "region": "Cervical", "type": "Osteopathic"},
        {"name": "Alar Ligament Stress Test", "region": "Cervical", "type": "Ortho"},
        {"name": "Sharp-Purser Test", "region": "Cervical", "type": "Neuro/Ortho"},
        {"name": "Vertebral Artery Test", "region": "Cervical", "type": "Neuro"},
        {"name": "Spurling’s Test", "region": "Cervical", "type": "Ortho"},
        {"name": "Foraminal Compression", "region": "Cervical", "type": "Ortho"},
        {"name": "Distraction Test", "region": "Cervical", "type": "Ortho"},
        {"name": "T1 Rib Spring", "region": "Cervical", "type": "Osteopathic"},
        {"name": "Rib Spring Test", "region": "Thoracic", "type": "Osteopathic"},
        {"name": "Pump Handle Test", "region": "Thoracic", "type": "Osteopathic"},
        {"name": "Bucket Handle Test", "region": "Thoracic", "type": "Osteopathic"},
        {"name": "T1–T12 Mobility", "region": "Thoracic", "type": "Osteopathic"},
        {"name": "Costovertebral Motion", "region": "Thoracic", "type": "Osteopathic"},
        {"name": "Thoracic Inlet Fascial Drag", "region": "Thoracic", "type": "Osteopathic"},
        {"name": "Pectoral Traction", "region": "Lymphatic", "type": "Osteopathic"},
        {"name": "Inguinal Ligament Palpation", "region": "Lymphatic", "type": "Osteopathic"},
        {"name": "Diaphragm Doming", "region": "Lymphatic", "type": "Osteopathic"},
        {"name": "Pedal Pump Test", "region": "Lymphatic", "type": "Osteopathic"},
        {"name": "Thoracic Inlet Congestion Test", "region": "Lymphatic", "type": "Osteopathic"},
        {"name": "SC Joint Motion", "region": "Shoulder", "type": "Osteopathic"},
        {"name": "AC Joint Shear", "region": "Shoulder", "type": "Ortho"},
        {"name": "Clavicle Spring Test", "region": "Shoulder", "type": "Osteopathic"},
        {"name": "GH Glide", "region": "Shoulder", "type": "Ortho"},
        {"name": "Apley’s Scratch Test", "region": "Shoulder", "type": "Ortho"},
        {"name": "Scapular Motion Testing", "region": "Shoulder", "type": "Osteopathic"},
        {"name": "Radial Head Spring Test", "region": "Elbow", "type": "Osteopathic"},
        {"name": "Valgus/Varus Elbow Stress", "region": "Elbow", "type": "Ortho"},
        {"name": "Wrist/Carpal Mobility", "region": "Wrist", "type": "Osteopathic"},
        {"name": "Lumbar Spring Test", "region": "Lumbar", "type": "Osteopathic"},
        {"name": "Seated Flexion Test", "region": "Pelvis", "type": "Osteopathic"},
        {"name": "Standing Flexion Test", "region": "Pelvis", "type": "Osteopathic"},
        {"name": "Pelvic Side Shift", "region": "Pelvis", "type": "Osteopathic"},
        {"name": "Trunk Sidebend ROM", "region": "Lumbar", "type": "Functional"},
        {"name": "ASIS/PSIS Landmark Test", "region": "Pelvis", "type": "Osteopathic"},
        {"name": "Innominate Rotation", "region": "Pelvis", "type": "Osteopathic"},
        {"name": "Pubic Symphysis Spring", "region": "Pelvis", "type": "Osteopathic"},
        {"name": "Sacral Spring Test", "region": "Sacrum", "type": "Osteopathic"},
        {"name": "Sacral Torsion Eval", "region": "Sacrum", "type": "Osteopathic"},
        {"name": "Sacral Sulcus Depth", "region": "Sacrum", "type": "Osteopathic"},
        {"name": "Gillet’s Test", "region": "SI Joint", "type": "Ortho"},
        {"name": "FABER Test", "region": "Hip", "type": "Ortho"},
        {"name": "Gaenslen’s Test", "region": "SI Joint", "type": "Ortho"},
        {"name": "Hip ER/IR Test", "region": "Hip", "type": "Ortho"},
        {"name": "Leg Length Assessment", "region": "Pelvis", "type": "Osteopathic"},
        {"name": "Supine-to-Sit Test", "region": "Pelvis", "type": "Osteopathic"},
        {"name": "Knee Valgus/Varus", "region": "Knee", "type": "Ortho"},
        {"name": "Anterior Drawer (Knee)", "region": "Knee", "type": "Ortho"},
        {"name": "Patellar Glide", "region": "Knee", "type": "Ortho"},
        {"name": "Talus Glide", "region": "Ankle", "type": "Osteopathic"},
        {"name": "Subtalar Joint Mobility", "region": "Foot", "type": "Ortho"},
        {"name": "Navicular Drop", "region": "Foot", "type": "Ortho"},
        {"name": "First Ray Mobility", "region": "Foot", "type": "Ortho"},
        {"name": "Cranial Nerve Test (I–XII)", "region": "Neuro", "type": "Neuro"},
        {"name": "Dermatomes", "region": "Neuro", "type": "Sensory"},
        {"name": "Myotomes", "region": "Neuro", "type": "Motor"},
        {"name": "DTRs: Biceps", "region": "Neuro", "type": "Reflex"},
        {"name": "DTRs: Triceps", "region": "Neuro", "type": "Reflex"},
        {"name": "DTRs: Patellar", "region": "Neuro", "type": "Reflex"},
        {"name": "DTRs: Achilles", "region": "Neuro", "type": "Reflex"},
        {"name": "Straight Leg Raise", "region": "Neuro", "type": "Ortho"},
        {"name": "Slump Test", "region": "Neuro", "type": "Ortho"},
        {"name": "Babinski Sign", "region": "Neuro", "type": "UMNL"},
        {"name": "Hoffmann’s Sign", "region": "Neuro", "type": "UMNL"},
        {"name": "Romberg Test", "region": "Neuro", "type": "Balance"},
        {"name": "Finger-to-Nose", "region": "Cerebellar", "type": "Motor Coordination"},
        {"name": "Rapid Alternating Movements", "region": "Cerebellar", "type": "Motor Coordination"},
        {"name": "Tandem Gait", "region": "Cerebellar", "type": "Motor Coordination"}
    ]

    return render_template("assessments.html", assessments=assessments)

# Global appointment list (temporary, until database)
appointments = []

@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        appointment = Appointment(
            patient_id = request.form.get("patient_id"),
            date = request.form.get("date"),
            time = request.form.get("time"),
            duration = int(request.form.get("duration")),
            notes = request.form.get("notes")
        )
        db.session.add(appointment)
        db.session.commit()
        return redirect(url_for("schedule"))

    # Load appointments from database
    appointments = Appointment.query.all()

    # Build patient dropdown list
    patient_choices = []
    for pid, data in patients.items():
        patient_choices.append({
            "id": pid,
            "name": f"{data['first_name']} {data['last_name']}"
        })

    return render_template(
        "schedule.html",
        appointments=appointments,
        patient_choices=patient_choices,
        patients=patients
    )

@app.route('/shifts', methods=["GET", "POST"])
def shifts():
    practitioners = Practitioner.query.all()

    if request.method == "POST":
        practitioner_id = request.form.get("practitioner_id")
        day = request.form.get("day_of_week")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")

        new_shift = Availability(
            practitioner_id=practitioner_id,
            day_of_week=day,
            start_time=start_time,
            end_time=end_time,
            is_available=True
        )
        db.session.add(new_shift)
        db.session.commit()

    all_shifts = Availability.query.all()
    return render_template("shifts.html", practitioners=practitioners, shifts=all_shifts)

@app.route("/save_shifts", methods=["POST"])
def save_shifts():
    from datetime import datetime
    data = request.get_json()
    shift_entries = data.get("shifts", [])
    practitioner_id = 1  # Replace this with dynamic practitioner ID later

    # Clear existing shifts for this practitioner first (optional)
    Availability.query.filter_by(practitioner_id=practitioner_id).delete()

    for entry in shift_entries:
        day, time_str = entry.split("|")
        time_obj = datetime.strptime(time_str, "%H:%M").time()

        new_shift = Availability(
            practitioner_id=practitioner_id,
            day_of_week=day,
            start_time=time_obj,
            end_time=(datetime.combine(datetime.today(), time_obj) + timedelta(minutes=5)).time(),
            is_available=True
        )
        db.session.add(new_shift)

    db.session.commit()
    return jsonify({"status": "success", "count": len(shift_entries)})

# ---------------------- MAIN ---------------------- #

if __name__ == '__main__':
    app.run(debug=True)






































































