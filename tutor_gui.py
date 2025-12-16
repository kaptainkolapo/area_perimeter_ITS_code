import math
import tkinter as tk
from tkinter import ttk, messagebox
from owlready2 import get_ontology, OwlReadyOntologyParsingError

ONTOLOGY_PATH = r"/Users/kolapoyusuf/Documents/AIC/areaperimeter.rdf"
TOLERANCE = 0.01


def get_first(lst, default=None):
    return lst[0] if lst else default


class StudentModel:
    def __init__(self):
        self.total = 0
        self.correct = 0
        self.incorrect = 0
        self.by_shape = {}
        self.wrong_by_shape = {}

    def record(self, shape_name: str, is_correct: bool):
        self.total += 1
        self.by_shape[shape_name] = self.by_shape.get(shape_name, 0) + 1
        if is_correct:
            self.correct += 1
        else:
            self.incorrect += 1
            self.wrong_by_shape[shape_name] = self.wrong_by_shape.get(shape_name, 0) + 1

    def summary_text(self) -> str:
        if self.total == 0:
            return "No attempts yet."
        acc = (self.correct / self.total) * 100
        lines = [
            f"Total attempts: {self.total}",
            f"Correct: {self.correct}",
            f"Incorrect: {self.incorrect}",
            f"Accuracy: {acc:.1f}%",
            "",
            "Attempts by shape:"
        ]
        for sh, cnt in self.by_shape.items():
            wrong = self.wrong_by_shape.get(sh, 0)
            lines.append(f"- {sh}: {cnt} attempt(s), {wrong} wrong")
        if self.wrong_by_shape:
            weakest = max(self.wrong_by_shape, key=self.wrong_by_shape.get)
            lines.append("")
            lines.append(f"Weak area: {weakest}")
            lines.append(f"Recommendation: practice more {weakest} questions.")
        else:
            lines.append("")
            lines.append("No weak area detected yet. Great job!")
        return "\n".join(lines)


class TutorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self._apply_style()

        self.title("Area & Perimeter Intelligent Tutor")
        self.geometry("1200x780")
        self.minsize(1100, 700)

        self.onto = None
        self.student_model = StudentModel()

        self.shape_instances = {}
        self.formulas_by_shape = {}

        self.area_task_ind = None
        self.perimeter_task_ind = None

        self._build_ui()
        self._load_ontology()
        self._refresh_inputs_and_question()

    # ---------- UI-3: Bigger fonts + spacing ----------
    def _apply_style(self):
        style = ttk.Style(self)

        available = style.theme_names()
        for preferred in ("clam", "vista", "aqua"):
            if preferred in available:
                style.theme_use(preferred)
                break

        # Larger global font for readability
        style.configure(".", font=("Arial", 13))
        style.configure("TButton", padding=10)
        style.configure("TLabel", padding=(4, 4))
        style.configure("TFrame", padding=8)

        # Group headers
        style.configure("TLabelframe", padding=14)
        style.configure("TLabelframe.Label", font=("Arial", 15, "bold"))

    # ---------- UI ----------
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # LEFT: Controls group
        controls = ttk.LabelFrame(self, text="Tutor Controls")
        controls.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        controls.columnconfigure(0, weight=1)

        ttk.Label(controls, text="Select shape:").grid(row=0, column=0, sticky="w")
        self.shape_var = tk.StringVar()
        self.shape_combo = ttk.Combobox(controls, textvariable=self.shape_var, state="readonly")
        self.shape_combo.grid(row=1, column=0, sticky="ew", pady=(2, 12))
        self.shape_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_inputs_and_question())

        ttk.Label(controls, text="Select task:").grid(row=2, column=0, sticky="w")
        self.task_var = tk.StringVar(value="Area")
        self.task_combo = ttk.Combobox(controls, textvariable=self.task_var, state="readonly", values=["Area", "Perimeter"])
        self.task_combo.grid(row=3, column=0, sticky="ew", pady=(2, 12))
        self.task_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_inputs_and_question())

        ttk.Separator(controls).grid(row=4, column=0, sticky="ew", pady=12)

        ttk.Label(controls, text="Enter dimensions:", font=("Arial", 14, "bold")).grid(row=5, column=0, sticky="w")
        self.inputs_frame = ttk.Frame(controls)
        self.inputs_frame.grid(row=6, column=0, sticky="ew", pady=(8, 12))
        self.inputs_frame.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Your answer:").grid(row=7, column=0, sticky="w")
        self.answer_var = tk.StringVar()
        self.answer_entry = ttk.Entry(controls, textvariable=self.answer_var)
        self.answer_entry.grid(row=8, column=0, sticky="ew", pady=(2, 12))

        btn_row = ttk.Frame(controls)
        btn_row.grid(row=9, column=0, sticky="ew")
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        self.submit_btn = ttk.Button(btn_row, text="Submit Answer", command=self._submit)
        self.submit_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.clear_btn = ttk.Button(btn_row, text="Clear", command=self._clear)
        self.clear_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # RIGHT: Output + Progress groups
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=14, pady=14)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=2)
        right.rowconfigure(1, weight=1)

        output_group = ttk.LabelFrame(right, text="Tutor Output (Feedback)")
        output_group.grid(row=0, column=0, sticky="nsew")
        output_group.columnconfigure(0, weight=1)
        output_group.rowconfigure(1, weight=1)

        self.question_lbl = ttk.Label(
            output_group,
            text="Question will appear here.",
            wraplength=780,
            font=("Arial", 15)
        )
        self.question_lbl.grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Output Text with Scrollbar
        out_frame = ttk.Frame(output_group)
        out_frame.grid(row=1, column=0, sticky="nsew")
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=1)

        self.output_box = tk.Text(out_frame, height=14, wrap="word", font=("Arial", 13))
        self.output_box.grid(row=0, column=0, sticky="nsew")
        out_scroll = ttk.Scrollbar(out_frame, orient="vertical", command=self.output_box.yview)
        out_scroll.grid(row=0, column=1, sticky="ns")
        self.output_box.configure(yscrollcommand=out_scroll.set, state="disabled")

        progress_group = ttk.LabelFrame(right, text="Progress Summary")
        progress_group.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        progress_group.columnconfigure(0, weight=1)
        progress_group.rowconfigure(0, weight=1)

        # Progress Text with Scrollbar
        prog_frame = ttk.Frame(progress_group)
        prog_frame.grid(row=0, column=0, sticky="nsew")
        prog_frame.columnconfigure(0, weight=1)
        prog_frame.rowconfigure(0, weight=1)

        self.progress_box = tk.Text(prog_frame, height=9, wrap="word", font=("Arial", 13))
        self.progress_box.grid(row=0, column=0, sticky="nsew")
        prog_scroll = ttk.Scrollbar(prog_frame, orient="vertical", command=self.progress_box.yview)
        prog_scroll.grid(row=0, column=1, sticky="ns")
        self.progress_box.configure(yscrollcommand=prog_scroll.set, state="disabled")

    # ---------- Ontology ----------
    def _load_ontology(self):
        try:
            self.onto = get_ontology(ONTOLOGY_PATH).load()
        except OwlReadyOntologyParsingError as e:
            messagebox.showerror("Ontology Error", f"Could not load ontology.\n\n{e}")
            self.destroy()
            return

        self.area_task_ind = self.onto.search_one(iri="*AreaTask")
        self.perimeter_task_ind = self.onto.search_one(iri="*PerimeterTask")
        if self.area_task_ind is None or self.perimeter_task_ind is None:
            messagebox.showerror(
                "Ontology Error",
                "AreaTask / PerimeterTask not found.\n\nMake sure TaskType individuals exist and are saved."
            )
            self.destroy()
            return

        for sh in self.onto.Shape.instances():
            self.shape_instances[sh.name] = sh

        for sh_name, sh in self.shape_instances.items():
            area_f = get_first(getattr(sh, "hasAreaFormula", []), None)
            per_f = get_first(getattr(sh, "hasPerimeterFormula", []), None)
            self.formulas_by_shape[sh_name] = {
                "Area": get_first(getattr(area_f, "hasDescription", []), None) if area_f else None,
                "Perimeter": get_first(getattr(per_f, "hasDescription", []), None) if per_f else None,
            }

        names = sorted(self.shape_instances.keys())
        self.shape_combo["values"] = names
        if names:
            self.shape_var.set(names[0])

    # ---------- Inputs + Question ----------
    def _required_dims(self, shape_name: str, task: str):
        if "Rectangle" in shape_name:
            return ["length", "width"]
        if "Square" in shape_name:
            return ["side"]
        if "Triangle" in shape_name:
            if task == "Area":
                return ["base", "height"]
            return ["side1", "side2", "side3"]
        if "Circle" in shape_name:
            return ["radius"]
        return []

    def _refresh_inputs_and_question(self):
        for w in self.inputs_frame.winfo_children():
            w.destroy()

        shape_name = self.shape_var.get()
        task = self.task_var.get()

        dims = self._required_dims(shape_name, task)
        self.dim_vars = {}

        for row, d in enumerate(dims):
            ttk.Label(self.inputs_frame, text=d.capitalize() + ":").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
            v = tk.StringVar()
            ttk.Entry(self.inputs_frame, textvariable=v).grid(row=row, column=1, sticky="ew", pady=4)
            self.dim_vars[d] = v

        nice_shape = shape_name.replace("Shape", "")
        dim_text = ", ".join(dims) if dims else "required values"
        self.question_lbl.config(text=f"Compute the {task.lower()} of a {nice_shape.lower()} using the given {dim_text}.")

    # ---------- Rule-based calculation ----------
    def _compute_correct_answer(self, shape_name: str, task: str, dims: dict) -> float:
        if "Rectangle" in shape_name:
            L, W = dims["length"], dims["width"]
            return (L * W) if task == "Area" else (2 * (L + W))

        if "Square" in shape_name:
            s = dims["side"]
            return (s * s) if task == "Area" else (4 * s)

        if "Triangle" in shape_name:
            if task == "Area":
                b, h = dims["base"], dims["height"]
                return 0.5 * b * h
            return dims["side1"] + dims["side2"] + dims["side3"]

        if "Circle" in shape_name:
            r = dims["radius"]
            return (math.pi * r * r) if task == "Area" else (2 * math.pi * r)

        raise ValueError("Unknown shape/task")

    # ---------- Ontology-based feedback retrieval ----------
    def _feedback_for(self, shape_name: str, task: str):
        shape_ind = self.shape_instances.get(shape_name)
        task_ind = self.area_task_ind if task == "Area" else self.perimeter_task_ind

        for fb in self.onto.Feedback.instances():
            fb_shape = get_first(getattr(fb, "feedbackForShape", []), None)
            fb_task = get_first(getattr(fb, "feedbackForTask", []), None)
            if fb_shape == shape_ind and fb_task == task_ind:
                fb_text = get_first(getattr(fb, "hasText", []), None)
                mc = get_first(getattr(fb, "addressesMisconception", []), None)
                mc_text = get_first(getattr(mc, "hasDescription", []), None) if mc else None
                if fb_text:
                    return fb_text, (mc_text or "A common mistake was detected for this topic.")

        return "Check the formula carefully and try again.", "No matching feedback found in the ontology for this shape/task."

    # ---------- Submit ----------
    def _submit(self):
        shape_name = self.shape_var.get()
        task = self.task_var.get()

        dims = {}
        try:
            for k, v in self.dim_vars.items():
                raw = v.get().strip()
                if raw == "":
                    raise ValueError(f"Missing value for {k}")
                val = float(raw)
                if val <= 0:
                    raise ValueError(f"{k} must be greater than 0")
                dims[k] = val
        except ValueError as e:
            messagebox.showwarning("Input error", str(e))
            return

        try:
            student_answer = float(self.answer_var.get().strip())
        except ValueError:
            messagebox.showwarning("Input error", "Please enter a valid numeric answer.")
            return

        correct_answer = self._compute_correct_answer(shape_name, task, dims)
        is_correct = abs(student_answer - correct_answer) <= TOLERANCE

        self.student_model.record(shape_name, is_correct)

        formula_text = self.formulas_by_shape.get(shape_name, {}).get(task)

        lines = []
        lines.append("✅ Correct!" if is_correct else "❌ Incorrect.")
        lines.append(f"Your answer: {student_answer}")
        lines.append(f"Correct answer: {correct_answer:.2f}")

        if formula_text:
            lines.append("")
            lines.append(f"Formula used (from ontology): {formula_text}")

        if not is_correct:
            fb_text, mc_text = self._feedback_for(shape_name, task)
            lines.append("")
            lines.append("Possible misconception (from ontology):")
            lines.append(f"- {mc_text}")
            lines.append("")
            lines.append("Feedback (from ontology):")
            lines.append(f"- {fb_text}")

        self._set_output("\n".join(lines))
        self._set_progress(self.student_model.summary_text())

    def _clear(self):
        self.answer_var.set("")
        for v in getattr(self, "dim_vars", {}).values():
            v.set("")
        self._set_output("")

    def _set_output(self, text):
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, text)
        self.output_box.configure(state="disabled")

    def _set_progress(self, text):
        self.progress_box.configure(state="normal")
        self.progress_box.delete("1.0", tk.END)
        self.progress_box.insert(tk.END, text)
        self.progress_box.configure(state="disabled")


if __name__ == "__main__":
    app = TutorApp()
    app.mainloop()
