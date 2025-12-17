from owlready2 import get_ontology, OwlReadyOntologyParsingError

ONTOLOGY_PATH = r"/Users/kolapoyusuf/Documents/AIC/areaperimeter.rdf"


def safe_float(prompt: str) -> float:
    while True:
        value = input(prompt).strip()
        try:
            return float(value)
        except ValueError:
            print("Please enter a valid number (e.g., 20 or 20.5).")


def get_first(lst, default=None):
    return lst[0] if lst else default


def get_shape_for_exercise(onto, exercise):
    for shape in onto.Shape.instances():
        if exercise in shape.hasExercise:
            return shape
    return None


def get_feedback_from_ontology(onto):
    for fb in onto.Feedback.instances():
        feedback_text = get_first(getattr(fb, "hasText", []), None)
        misconception = get_first(getattr(fb, "addressesMisconception", []), None)
        misconception_text = None

        if misconception is not None:
            misconception_text = get_first(getattr(misconception, "hasDescription", []), None)

        if feedback_text:
            return feedback_text, misconception_text

    return None, None


# ---------------- Student Model (Step 8) ----------------
class StudentModel:
    def __init__(self):
        self.total_attempts = 0
        self.correct_attempts = 0
        self.incorrect_attempts = 0
        self.attempts_by_shape = {}       # e.g. {"Rectangle": 2, "Circle": 1}
        self.incorrect_by_shape = {}      # e.g. {"Rectangle": 1}

    def record_attempt(self, shape_name: str, is_correct: bool):
        self.total_attempts += 1

        self.attempts_by_shape[shape_name] = self.attempts_by_shape.get(shape_name, 0) + 1

        if is_correct:
            self.correct_attempts += 1
        else:
            self.incorrect_attempts += 1
            self.incorrect_by_shape[shape_name] = self.incorrect_by_shape.get(shape_name, 0) + 1

    def print_summary(self):
        print("\n=== Progress Summary (Student Model) ===")
        print("Total attempts:", self.total_attempts)
        print("Correct:", self.correct_attempts)
        print("Incorrect:", self.incorrect_attempts)

        if self.total_attempts > 0:
            accuracy = (self.correct_attempts / self.total_attempts) * 100
            print(f"Accuracy: {accuracy:.1f}%")

        print("\nAttempts by shape:")
        for shape, count in self.attempts_by_shape.items():
            wrong = self.incorrect_by_shape.get(shape, 0)
            print(f"- {shape}: {count} attempt(s), {wrong} wrong")

        if self.incorrect_by_shape:
            weakest_shape = max(self.incorrect_by_shape, key=self.incorrect_by_shape.get)
            print("\nWeak area detected:", weakest_shape)
            print("Recommendation: Practice more questions on", weakest_shape)
        else:
            print("\nNo weak area detected yet. Great job!")


def main():
    print("Loading ontology from:", ONTOLOGY_PATH)

    try:
        onto = get_ontology(ONTOLOGY_PATH).load()
    except OwlReadyOntologyParsingError as e:
        print("\n*** Ontology parsing failed ***")
        print("Error:", e)
        return

    print("\nOntology loaded successfully!\n")

    exercises = list(onto.Exercise.instances())
    if not exercises:
        print("No exercises found in the ontology.")
        return

    # Create student model
    student_model = StudentModel()

    # For now: run ONE attempt per program execution (simple prototype)
    ex = exercises[0]

    print("=== Area & Perimeter Tutor ===")
    print("Exercise:", ex.name)

    description = get_first(ex.hasDescription, "No description available.")
    print("Question:", description)

    student_answer = safe_float("Your answer: ")

    correct_answer = get_first(ex.hasCorrectAnswer, None)
    if correct_answer is None:
        print("No correct answer stored in ontology.")
        return

    correct_answer = float(correct_answer)

    tolerance = 0.01
    is_correct = abs(student_answer - correct_answer) <= tolerance

    # Find shape and formulas
    shape = get_shape_for_exercise(onto, ex)
    shape_name = shape.name if shape else "UnknownShape"

    # Update student model (Step 8)
    student_model.record_attempt(shape_name, is_correct)

    area_formula_text = None
    perimeter_formula_text = None

    if shape:
        area_formula = get_first(shape.hasAreaFormula, None)
        per_formula = get_first(shape.hasPerimeterFormula, None)

        if area_formula:
            area_formula_text = get_first(area_formula.hasDescription, None)
        if per_formula:
            perimeter_formula_text = get_first(per_formula.hasDescription, None)

    # Output feedback
    if is_correct:
        print("\nCorrect!")
        print("Correct answer =", correct_answer)
    else:
        print("\n Incorrect.")
        print("Your answer =", student_answer)
        print("Correct answer =", correct_answer)

        fb_text, mc_text = get_feedback_from_ontology(onto)

        if mc_text:
            print("\nPossible misconception (from ontology):")
            print("-", mc_text)

        if fb_text:
            print("\nFeedback (from ontology):")
            print("-", fb_text)

    # Explainable AI: show formula
    if shape:
        print("\nLinked shape:", shape.name)
        desc_lower = str(description).lower()
        if "perimeter" in desc_lower or "circumference" in desc_lower:
            if perimeter_formula_text:
                print("Formula used (from ontology):", perimeter_formula_text)
        else:
            if area_formula_text:
                print("Formula used (from ontology):", area_formula_text)

    print("\n--- End of attempt ---")

    # Print student progress summary (Step 8)
    student_model.print_summary()


if __name__ == "__main__":
    main()
