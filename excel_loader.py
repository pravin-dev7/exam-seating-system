# excel_loader.py - Excel File Handler

import pandas as pd
import os


def validate_excel_format(filepath):
    """
    Validate that the uploaded Excel file has the correct format.
    Expected columns: RollNo, Department
    Returns (is_valid: bool, message: str)
    """
    try:
        df = pd.read_excel(filepath)

        # Normalize column names
        df.columns = [str(col).strip().lower() for col in df.columns]

        required_columns = {'rollno', 'department'}
        actual_columns = set(df.columns)

        # Check for required columns (case-insensitive)
        if not required_columns.issubset(actual_columns):
            missing = required_columns - actual_columns
            return False, f"Missing required columns: {', '.join(missing)}. Expected: RollNo, Department"

        if len(df) == 0:
            return False, "Excel file is empty. Please upload a file with student data."

        # Check for null values in key columns
        if df['rollno'].isnull().any():
            return False, "RollNo column contains empty values. Please fix and re-upload."

        if df['department'].isnull().any():
            return False, "Department column contains empty values. Please fix and re-upload."

        # Check for duplicate roll numbers
        if df['rollno'].duplicated().any():
            dupes = df[df['rollno'].duplicated()]['rollno'].tolist()
            return False, f"Duplicate Roll Numbers found: {dupes[:5]}. Please fix and re-upload."

        return True, f"File validated successfully. {len(df)} students found."

    except Exception as e:
        return False, f"Error reading Excel file: {str(e)}"


def load_students_from_excel(filepath):
    """
    Load student data from Excel file.
    Returns list of dicts: [{'roll_no': '101', 'department': 'CSE'}, ...]
    """
    try:
        df = pd.read_excel(filepath)

        # Normalize column names
        df.columns = [str(col).strip().lower() for col in df.columns]

        students = []
        for _, row in df.iterrows():
            students.append({
                'roll_no': str(row['rollno']).strip(),
                'department': str(row['department']).strip().upper()
            })

        return students, None

    except Exception as e:
        return None, f"Error loading students: {str(e)}"


def get_department_summary(students):
    """
    Returns a summary dict of departments and their student counts.
    Example: {'CSE': 40, 'IT': 30, 'ECE': 30}
    """
    summary = {}
    for s in students:
        dept = s['department']
        summary[dept] = summary.get(dept, 0) + 1
    return summary
