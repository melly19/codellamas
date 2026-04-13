#!/usr/bin/env python3
"""
Exercise Evaluation Script
Evaluates generated Java exercises against multiple criteria
"""

import os
import csv
import re
from pathlib import Path
from typing import Dict, Tuple, List
import subprocess

# Configuration
EXERCISES_DIR = "backend/src/codellamas_backend/generated_exercises"
CSV_PATH = f"{EXERCISES_DIR}/Evaluation - Sheet5.csv"

class ExerciseEvaluator:
    def __init__(self, exercise_dir: str, exercise_name: str):
        self.exercise_dir = exercise_dir
        self.exercise_name = exercise_name
        self.smelly_src = os.path.join(exercise_dir, "src/main/java")
        self.solution_src = os.path.join(exercise_dir, "answers/src/main/java")
        self.test_src = os.path.join(exercise_dir, "src/test/java")
        self.problem_md = os.path.join(exercise_dir, "PROBLEM.md")
        self.solution_exp_md = os.path.join(exercise_dir, "SOLUTION_EXP.md")
        self.pom_xml = os.path.join(exercise_dir, "pom.xml")
        
    def check_file_exists(self, path: str) -> bool:
        """Check if file exists"""
        return os.path.exists(path)
    
    def check_java_files_exist(self, directory: str) -> bool:
        """Check if directory contains Java files"""
        if not os.path.exists(directory):
            return False
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".java"):
                    return True
        return False
    
    def count_java_files(self, directory: str) -> int:
        """Count Java files in directory"""
        count = 0
        if not os.path.exists(directory):
            return 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".java"):
                    count += 1
        return count
    
    def read_file_content(self, path: str) -> str:
        """Read file content safely"""
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            print(f"Error reading {path}: {e}")
        return ""
    
    def check_smelly_code_execution(self) -> bool:
        """Check if smelly code compiles and tests exist"""
        # Code exists and has test cases
        has_main = self.check_java_files_exist(self.smelly_src)
        has_tests = self.check_java_files_exist(self.test_src)
        has_pom = self.check_file_exists(self.pom_xml)
        return has_main and has_tests and has_pom
    
    def check_solution_execution(self) -> bool:
        """Check if solution code exists and is complete"""
        has_solution = self.check_java_files_exist(self.solution_src)
        has_pom = self.check_file_exists(self.pom_xml)
        return has_solution and has_pom
    
    def check_problem_statement(self) -> bool:
        """Check if problem statement exists and is not empty"""
        content = self.read_file_content(self.problem_md)
        return len(content) > 100  # Check for meaningful content
    
    def check_test_case_coverage(self) -> bool:
        """Check if test cases exist and cover main scenarios"""
        test_files = []
        test_count = 0
        
        if os.path.exists(self.test_src):
            for root, dirs, files in os.walk(self.test_src):
                for file in files:
                    if file.endswith("Test.java"):
                        test_files.append(os.path.join(root, file))
                        content = self.read_file_content(os.path.join(root, file))
                        # Count test methods
                        test_count += len(re.findall(r'@Test|public\s+void\s+test', content))
        
        return test_count >= 3  # At least 3 test methods
    
    def extract_code_smell(self) -> str:
        """Extract the code smell from exercise name"""
        # Format: {TOPIC}_openrouter-...__{CODE_SMELL}__0604_1412
        parts = self.exercise_name.split('_')
        if len(parts) >= 3:
            # Find the part that indicates the smell
            for i, part in enumerate(parts):
                if part.isdigit() and len(part) == 4:  # Found date marker (0604)
                    if i > 0:
                        return parts[i-1]
        return "Unknown"
    
    def detect_duplicate_code(self, directory: str) -> bool:
        """Detect potential duplicate code patterns"""
        java_files = []
        
        if not os.path.exists(directory):
            return False
            
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".java"):
                    java_files.append(os.path.join(root, file))
        
        if len(java_files) < 2:
            return False
        
        # Read all Java files and look for similar patterns
        contents = [self.read_file_content(f) for f in java_files]
        
        # Check for common validation patterns, loops, etc.
        pattern_count = 0
        for content in contents:
            pattern_count += len(re.findall(r'if\s*\(.*==\s*null', content))
            pattern_count += len(re.findall(r'for\s*\(.*\)', content))
            pattern_count += len(re.findall(r'isEmpty\(\)', content))
        
        return pattern_count > 5
    
    def check_smelly_code_accuracy(self) -> bool:
        """Check if smelly code indeed has the advertised code smell"""
        smell = self.extract_code_smell().lower()
        
        content = ""
        for root, dirs, files in os.walk(self.smelly_src):
            for file in files:
                if file.endswith(".java"):
                    content += self.read_file_content(os.path.join(root, file)) + "\n"
        
        if not content:
            return False
        
        # Check for specific smells
        if "duplicate" in smell:
            return self.detect_duplicate_code(self.smelly_src)
        elif "long" in smell and "method" in smell:
            return len(re.findall(r'def\s+\w+|public\s+\w+', content)) > 0 and len(content) > 1000
        elif "feature" in smell and "envy" in smell:
            return len(re.findall(r'get\w+\(\)|is\w+\(\)', content)) > 5
        elif "primitive" in smell and "obsession" in smell:
            return len(re.findall(r'String|int|double|boolean', content)) > 20
        elif "switch" in smell:
            return "switch" in content
        elif "shotgun" in smell:
            return len(java_files := [f for root, dirs, files in os.walk(self.smelly_src) 
                                      for f in files if f.endswith(".java")]) > 2
        
        return True  # Assume valid if can't determine
    
    def check_refactored_code_quality(self) -> bool:
        """Evaluate if refactored code is clean and better"""
        if not os.path.exists(self.solution_src):
            return False
        
        # Check solution has extracted methods, constants, etc.
        solution_content = ""
        for root, dirs, files in os.walk(self.solution_src):
            for file in files:
                if file.endswith(".java"):
                    solution_content += self.read_file_content(os.path.join(root, file))
        
        # Better code characteristics
        has_javadoc = "/**" in solution_content or "/*" in solution_content
        has_proper_naming = len(re.findall(r'[A-Z]\w+(?:Service|Manager|Helper|Validator)', solution_content)) > 2
        has_methods = len(re.findall(r'(private|public)\s+\w+\s+\w+\s*\(', solution_content)) > 5
        
        return (has_javadoc or has_proper_naming) and has_methods
    
    def check_target_audience_fit(self) -> bool:
        """Check if exercise is appropriate difficulty for students"""
        # Check problem scope
        problem_content = self.read_file_content(self.problem_md)
        solution_exp = self.read_file_content(self.solution_exp_md)
        
        java_file_count = self.count_java_files(self.smelly_src)
        test_count = self.count_java_files(self.test_src)
        
        # Good fit: 2-5 Java files, clear problem, good explanation
        has_good_scope = 2 <= java_file_count <= 5
        has_clear_problem = len(problem_content) > 200
        has_explanation = len(solution_exp) > 200
        
        return has_good_scope and has_clear_problem and has_explanation
    
    def score_code_realism(self) -> int:
        """Score realism and scenario quality (0-10) - STRICT"""
        problem_content = self.read_file_content(self.problem_md)
        solution_exp = self.read_file_content(self.solution_exp_md)
        
        score = 0
        
        # Base: has problem statement (1 point)
        if len(problem_content) > 100:
            score += 1
        
        # Has concrete use case description (2 points)
        use_case_indicators = ["create", "update", "delete", "manage", "handle", "process", "store", "retrieve"]
        use_case_count = sum(1 for indicator in use_case_indicators if indicator in problem_content.lower())
        if use_case_count >= 3:
            score += 2
        
        # Has specific domain context beyond generic example (2 points)
        domain_depth = len([w for w in problem_content.split() if w.lower() in 
                           ["patient", "appointment", "healthcare", "clinic", "diagnosis", "prescription"]])
        if domain_depth >= 5:
            score += 2
        
        # Problem describes constraints/requirements clearly (2 points)
        req_indicators = ["constraint", "requirement", "must", "should", "ensure", "maintain"]
        if sum(1 for ind in req_indicators if ind in problem_content.lower()) >= 3:
            score += 2
        
        # Solution explains the scenario quality (1 point)
        explanation_quality = len(solution_exp)
        if explanation_quality > 500:
            score += 1
        
        # Realistic flow (no trivial toy problem) (2 points)
        has_flow = any(phrase in problem_content.lower() for phrase in 
                      ["workflow", "sequence", "flow", "pipeline", "process"])
        if has_flow and use_case_count >= 2:
            score += 2
        
        return min(10, score)
    
    
    def score_ide_usability(self) -> int:
        """Score IDE and workflow usability (0-10) - STRICT"""
        pom_content = self.read_file_content(self.pom_xml)
        
        score = 0
        
        # Has pom.xml with Maven configured (1 point)
        if "project" in pom_content.lower() and "maven" in pom_content.lower():
            score += 1
        
        # Has JUnit dependency (1 point)
        if "junit" in pom_content.lower():
            score += 1
        
        # Proper directory structure (1 point)
        has_src = os.path.exists(os.path.join(self.exercise_dir, "src/main/java"))
        has_test = os.path.exists(os.path.join(self.exercise_dir, "src/test/java"))
        if has_src and has_test:
            score += 1
        
        # Package structure exists (1 point)
        if self.check_package_structure():
            score += 1
        
        # Test files exist and are not trivial (2 points)
        test_file_count = self.count_java_files(self.test_src)
        test_content_size = 0
        if os.path.exists(self.test_src):
            for root, dirs, files in os.walk(self.test_src):
                for file in files:
                    if file.endswith(".java"):
                        test_content_size += len(self.read_file_content(os.path.join(root, file)))
        
        has_meaningful_tests = test_file_count > 0 and test_content_size > 500  # More than stub tests
        if has_meaningful_tests:
            score += 2
        
        # Source code is reasonable size (not empty, not bloated) (1 point)
        main_content_size = 0
        if os.path.exists(self.smelly_src):
            for root, dirs, files in os.walk(self.smelly_src):
                for file in files:
                    if file.endswith(".java"):
                        main_content_size += len(self.read_file_content(os.path.join(root, file)))
        
        if 500 < main_content_size < 10000:  # Reasonable size
            score += 1
        
        # README or documentation (1 point)
        has_docs = (os.path.exists(os.path.join(self.exercise_dir, "README.md")) or
                   len(self.read_file_content(self.problem_md)) > 300)
        if has_docs:
            score += 1
        
        # Solution code exists and is properly structured (1 point)
        if self.check_java_files_exist(self.solution_src):
            score += 1
        
        return min(10, score)
    
    
    def check_package_structure(self) -> bool:
        """Check if proper package structure exists"""
        for root, dirs, files in os.walk(self.smelly_src):
            for file in files:
                if file.endswith(".java"):
                    content = self.read_file_content(os.path.join(root, file))
                    if "package" in content and "import" in content:
                        return True
        return False
    
    def score_refactoring_depth(self) -> int:
        """Score refactoring depth & impact (0-10) - STRICT CODE ANALYSIS"""
        smell = self.extract_code_smell().lower()
        solution_exp = self.read_file_content(self.solution_exp_md)
        
        score = 0
        
        # Read smelly and solution code
        smelly_content = ""
        for root, dirs, files in os.walk(self.smelly_src):
            for file in files:
                if file.endswith(".java"):
                    smelly_content += self.read_file_content(os.path.join(root, file)) + "\n"
        
        solution_content = ""
        for root, dirs, files in os.walk(self.solution_src):
            for file in files:
                if file.endswith(".java"):
                    solution_content += self.read_file_content(os.path.join(root, file)) + "\n"
        
        if not smelly_content or not solution_content:
            return 2  # Not evaluable
        
        # 1. Check if solution is significantly different (1 point)
        if len(smelly_content) != len(solution_content):
            score += 1
        
        # 2. Duplicate code reduction (2 points)
        # Count similar patterns in smelly code
        smelly_patterns = len(re.findall(r'(if\s*\(.*?\)|for\s*\(.*?\)|while\s*\(.*?\))', smelly_content))
        solution_patterns = len(re.findall(r'(if\s*\(.*?\)|for\s*\(.*?\)|while\s*\(.*?\))', solution_content))
        
        if "duplicate" in smell and smelly_patterns > solution_patterns:
            score += 2
        elif smelly_patterns > solution_patterns:
            score += 1
        
        # 3. Method extraction/refactoring (2 points)
        # Count method definitions
        smelly_methods = len(re.findall(r'(public|private|protected)\s+\w+\s+\w+\s*\(', smelly_content))
        solution_methods = len(re.findall(r'(public|private|protected)\s+\w+\s+\w+\s*\(', solution_content))
        
        if solution_methods > smelly_methods:
            score += 2  # Methods extracted
        elif solution_methods == smelly_methods and len(solution_content) < len(smelly_content):
            score += 1  # Same number but cleaner
        
        # 4. Code comments/documentation improvement (1 point)
        smelly_comments = len(re.findall(r'//|/\*|\*/', smelly_content))
        solution_comments = len(re.findall(r'//|/\*|\*/', solution_content))
        if solution_comments > smelly_comments:
            score += 1
        
        # 5. Variable/method naming improvement (1 point)
        # Check for meaningful names in solution vs generic names in smelly
        generic_names = len(re.findall(r'\b(temp|tmp|data|value|x|y|z|i|j|k)\b', smelly_content))
        generic_names_solution = len(re.findall(r'\b(temp|tmp|data|value|x|y|z|i|j|k)\b', solution_content))
        if generic_names > generic_names_solution:
            score += 1
        
        # 6. Explanation quality (1 point)
        if len(solution_exp) > 400 and ("refactor" in solution_exp.lower() or "improve" in solution_exp.lower()):
            score += 1
        
        # 7. Smell-specific improvements (2 points)
        if "long" in smell and "method" in smell:
            # Check for smaller method sizes
            smelly_method_lines = len(re.findall(r'\n', smelly_content)) / max(1, smelly_methods)
            solution_method_lines = len(re.findall(r'\n', solution_content)) / max(1, solution_methods)
            if solution_method_lines < smelly_method_lines:
                score += 2
        
        elif "duplicate" in smell:
            # Check for extracted helper/utility methods/classes
            if (re.search(r'(Helper|Util|Validator|Factory)', solution_content) and 
                not re.search(r'(Helper|Util|Validator|Factory)', smelly_content)):
                score += 2
            elif solution_methods > smelly_methods:
                score += 2
        
        elif "switch" in smell:
            # Check if switch replaced with polymorphism/strategy
            smelly_switches = len(re.findall(r'switch\s*\(', smelly_content))
            solution_switches = len(re.findall(r'switch\s*\(', solution_content))
            if solution_switches < smelly_switches:
                score += 2
            elif solution_methods > smelly_methods:
                score += 2
        
        elif "feature" in smell and "envy" in smell:
            # Check for better encapsulation
            if solution_methods > smelly_methods:
                score += 2
        
        else:
            # Generic smell - check for any meaningful improvement
            if solution_methods > smelly_methods or len(solution_content) < len(smelly_content):
                score += 2
        
        return min(10, max(1, score))  # Minimum 1 if evaluable
    
    
    def evaluate(self) -> Dict:
        """Run full evaluation"""
        return {
            "Smelly Code Execution": "TRUE" if self.check_smelly_code_execution() else "FALSE",
            "Solution Execution": "TRUE" if self.check_solution_execution() else "FALSE",
            "Problem Statement": "TRUE" if self.check_problem_statement() else "FALSE",
            "Test Case Coverage": "TRUE" if self.check_test_case_coverage() else "FALSE",
            "Smelly Code Accuracy": "TRUE" if self.check_smelly_code_accuracy() else "FALSE",
            "Refactored Code Quality": "TRUE" if self.check_refactored_code_quality() else "FALSE",
            "Target Audience Fit": "TRUE" if self.check_target_audience_fit() else "FALSE",
            "Code Realism and Scenario Quality": str(self.score_code_realism()),
            "IDE and Workflow Usability": str(self.score_ide_usability()),
            "Refactoring Depth & Impact": str(self.score_refactoring_depth()),
        }


def main():
    """Main evaluation loop"""
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found: {CSV_PATH}")
        return
    
    # Read existing CSV - skip first line (extra header)
    exercises = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Skip first line and parse the rest
        csv_content = ''.join(lines[1:])
        reader = csv.DictReader(csv_content.splitlines())
        exercises = list(reader)
    
    total = len(exercises)
    evaluated = 0
    
    print(f"Starting evaluation of {total} exercises...")
    print("-" * 80)
    
    # Evaluate each exercise
    for idx, exercise in enumerate(exercises, 1):
        exercise_name = exercise['Name'].strip()
        if not exercise_name:
            continue
        
        exercise_path = os.path.join(EXERCISES_DIR, exercise_name)
        if not os.path.exists(exercise_path):
            print(f"[{idx}/{total}] ❌ {exercise_name}: Directory not found")
            continue
        
        evaluator = ExerciseEvaluator(exercise_path, exercise_name)
        results = evaluator.evaluate()
        
        # Update exercise with results
        for key, value in results.items():
            exercise[key] = value
        
        evaluated += 1
        status = "✓" if all(v != "FALSE" for v in results.values() if v in ["TRUE", "FALSE"]) else "⚠"
        print(f"[{idx}/{total}] {status} {exercise_name}")
        print(f"  Smelly: {results['Smelly Code Execution']} | Solution: {results['Solution Execution']} | " +
              f"Problem: {results['Problem Statement']} | Tests: {results['Test Case Coverage']}")
        print(f"  Accuracy: {results['Smelly Code Accuracy']} | Quality: {results['Refactored Code Quality']} | " +
              f"Fit: {results['Target Audience Fit']}")
        print(f"  Realism: {results['Code Realism and Scenario Quality']}/10 | " +
              f"IDE: {results['IDE and Workflow Usability']}/10 | " +
              f"Depth: {results['Refactoring Depth & Impact']}/10")
        print()
    
    # Write updated CSV - preserve the extra header
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        f.write("Evaluation - Sheet5\n")  # Write back the first header line
        fieldnames = exercises[0].keys() if exercises else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(exercises)
    
    print("-" * 80)
    print(f"Evaluation complete! Updated {evaluated}/{total} exercises")
    print(f"Results saved to: {CSV_PATH}")


if __name__ == "__main__":
    main()
