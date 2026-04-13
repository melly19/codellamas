#!/usr/bin/env python3
"""
Interactive Exercise Evaluator
Evaluates exercises one at a time and allows manual review/adjustments
"""

import os
import csv
from pathlib import Path
from typing import Dict, Tuple

EXERCISES_DIR = "backend/src/codellamas_backend/generated_exercises"
CSV_PATH = f"{EXERCISES_DIR}/Evaluation - Sheet5.csv"

class InteractiveEvaluator:
    """Interactive evaluation of exercises with manual review capability"""
    
    def __init__(self):
        self.exercises_dir = EXERCISES_DIR
        self.csv_path = CSV_PATH
        self.current_index = 0
        self.exercises = self.load_csv()
        
    def load_csv(self):
        """Load exercises from CSV"""
        exercises = []
        if os.path.exists(self.csv_path):
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                csv_content = ''.join(lines[1:])  # Skip first header
                reader = csv.DictReader(csv_content.splitlines())
                exercises = list(reader)
        return exercises
    
    def save_csv(self):
        """Save exercises back to CSV"""
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            f.write("Evaluation - Sheet5\n")
            if self.exercises:
                fieldnames = self.exercises[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.exercises)
    
    def get_exercise_summary(self, exercise: Dict) -> str:
        """Get summary of exercise contents"""
        name = exercise.get('Name', 'Unknown')
        exercise_path = os.path.join(self.exercises_dir, name)
        
        # Extract code smell from name
        parts = name.split('_')
        for i, part in enumerate(parts):
            if part.isdigit() and len(part) == 4:  # Date marker
                code_smell = parts[i-1] if i > 0 else 'Unknown'
                break
        else:
            code_smell = 'Unknown'
        
        # Check what exists
        has_smelly = os.path.exists(os.path.join(exercise_path, "src/main/java"))
        has_solution = os.path.exists(os.path.join(exercise_path, "answers/src/main/java"))
        has_tests = os.path.exists(os.path.join(exercise_path, "src/test/java"))
        
        summary = f"""
╔════════════════════════════════════════════════════════════════╗
║ EXERCISE: {code_smell.upper()}
╚════════════════════════════════════════════════════════════════╝

Name: {name}
Path: {exercise_path}

Status:
  ✓ Smelly Code (src/main): {has_smelly}
  ✓ Solution Code: {has_solution}
  ✓ Test Cases: {has_tests}

Files to Review:
  • PROBLEM.md - Problem description
  • SOLUTION_EXP.md - Explanation
  • src/main/java/ - Student sees this
  • answers/src/main/java/ - Reference solution
  • src/test/java/ - Test cases
"""
        return summary
    
    def get_current_evaluation(self) -> Dict:
        """Get current evaluation state"""
        return self.exercises[self.current_index] if self.current_index < len(self.exercises) else {}
    
    def show_evaluation_status(self):
        """Show current evaluation status"""
        exercise = self.get_current_evaluation()
        if not exercise.get('Name'):
            print("No more exercises to evaluate")
            return
        
        print(f"\n[{self.current_index + 1}/{len(self.exercises)}] Current Evaluation Status:")
        print(f"\nExercise: {exercise.get('Name')}")
        print("\nBoolean Criteria:")
        bool_criteria = [
            'Smelly Code Execution', 'Solution Execution', 'Problem Statement',
            'Test Case Coverage', 'Smelly Code Accuracy', 'Refactored Code Quality',
            'Target Audience Fit'
        ]
        for criterion in bool_criteria:
            value = exercise.get(criterion, '?')
            print(f"  {criterion:30s}: {value}")
        
        print("\nNumeric Criteria (0-10):")
        numeric_criteria = [
            'Code Realism and Scenario Quality',
            'IDE and Workflow Usability', 
            'Refactoring Depth & Impact'
        ]
        for criterion in numeric_criteria:
            value = exercise.get(criterion, '?')
            print(f"  {criterion:30s}: {value}")
    
    def update_field(self, field_name: str, value: str) -> bool:
        """Update a field in current exercise"""
        if self.current_index >= len(self.exercises):
            print("Invalid exercise index")
            return False
        
        exercise = self.exercises[self.current_index]
        exercise[field_name] = value
        print(f"✓ Updated {field_name} = {value}")
        self.save_csv()
        return True
    
    def interactive_evaluate(self):
        """Interactive evaluation mode"""
        while self.current_index < len(self.exercises):
            exercise = self.get_current_evaluation()
            
            if not exercise.get('Name'):
                self.current_index += 1
                continue
            
            print(self.get_exercise_summary(exercise))
            self.show_evaluation_status()
            
            print("\n" + "="*60)
            print("Commands:")
            print("  TRUE/FALSE criteria: type 'smelly=TRUE' or 'solution=FALSE'")
            print("  Numeric criteria: type 'realism=7' or 'ide=9' or 'depth=5'")
            print("  Full list: smelly, solution, problem, tests, accuracy, quality, fit")
            print("             realism, ide, depth")
            print("  Navigation: 'skip', 'prev', 'eval' (show status), 'next'/'done'")
            print("="*60)
            
            while True:
                cmd = input(f"\n[{self.current_index + 1}/{len(self.exercises)}] Command: ").strip().lower()
                
                if cmd == 'done' or cmd == 'next':
                    self.current_index += 1
                    break
                elif cmd == 'skip':
                    self.current_index += 1
                    break
                elif cmd == 'prev':
                    if self.current_index > 0:
                        self.current_index -= 1
                    break
                elif cmd == 'eval':
                    self.show_evaluation_status()
                elif '=' in cmd:
                    # Parse field=value
                    parts = cmd.split('=', 1)
                    if len(parts) == 2:
                        field_short, value = parts[0].strip(), parts[1].strip()
                        
                        # Map short names to full names
                        field_map = {
                            'smelly': 'Smelly Code Execution',
                            'solution': 'Solution Execution',
                            'problem': 'Problem Statement',
                            'tests': 'Test Case Coverage',
                            'accuracy': 'Smelly Code Accuracy',
                            'quality': 'Refactored Code Quality',
                            'fit': 'Target Audience Fit',
                            'realism': 'Code Realism and Scenario Quality',
                            'ide': 'IDE and Workflow Usability',
                            'depth': 'Refactoring Depth & Impact'
                        }
                        
                        if field_short in field_map:
                            full_field = field_map[field_short]
                            self.update_field(full_field, value)
                        else:
                            print(f"Unknown field: {field_short}")
                    else:
                        print("Invalid format. Use field=value")
                elif cmd == 'quit' or cmd == 'exit':
                    print("Exiting...")
                    return
                else:
                    print("Unknown command")
        
        print("\n✅ All exercises processed!")
        self.save_csv()

def main():
    evaluator = InteractiveEvaluator()
    print(f"\n📊 Interactive Exercise Evaluator")
    print(f"Total exercises: {len(evaluator.exercises)}")
    evaluator.interactive_evaluate()

if __name__ == "__main__":
    main()
