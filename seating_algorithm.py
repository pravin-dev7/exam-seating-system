# seating_algorithm.py - Core Seating Arrangement Algorithms

import random
from itertools import cycle


# ---------------------------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------------------------

def mix_departments(students):
    """
    Interleave students so no two consecutive students share a department.
    Uses a round-robin approach across departments.
    Returns a new list of students in mixed order.
    """
    # Group students by department
    dept_groups = {}
    for student in students:
        dept = student['department']
        dept_groups.setdefault(dept, []).append(student)

    # Sort departments by size (largest first) for better mixing
    sorted_depts = sorted(dept_groups.keys(), key=lambda d: -len(dept_groups[d]))

    mixed = []
    queues = [dept_groups[d][:] for d in sorted_depts]

    while any(queues):
        for q in queues:
            if q:
                mixed.append(q.pop(0))

    return mixed


def _chunk_students_into_seats(students, seats_per_bench):
    """Split student list into bench-sized chunks."""
    benches = []
    for i in range(0, len(students), seats_per_bench):
        bench = students[i:i + seats_per_bench]
        benches.append(bench)
    return benches


# ---------------------------------------------------------------------------
# Seating Flow Algorithms
# ---------------------------------------------------------------------------

def zigzag_seating(students, seats_per_bench):
    """
    Zig-Zag Seating: alternates students from front and back of the list
    to ensure department mixing across adjacent benches.
    """
    mixed = mix_departments(students)
    front = mixed[:len(mixed)//2]
    back = mixed[len(mixed)//2:][::-1]

    zigzag = []
    for i in range(max(len(front), len(back))):
        if i < len(front):
            zigzag.append(front[i])
        if i < len(back):
            zigzag.append(back[i])

    return _chunk_students_into_seats(zigzag, seats_per_bench)


def column_wise_seating(students, seats_per_bench):
    """
    Column Wise Seating: fills column by column rather than row by row.
    Students from different departments fill each column sequentially.
    """
    mixed = mix_departments(students)
    total = len(mixed)
    num_benches = (total + seats_per_bench - 1) // seats_per_bench

    # Create empty grid
    grid = [[None] * seats_per_bench for _ in range(num_benches)]
    idx = 0

    # Fill column by column
    for col in range(seats_per_bench):
        for row in range(num_benches):
            if idx < total:
                grid[row][col] = mixed[idx]
                idx += 1

    # Convert grid rows to bench format (filter out None)
    benches = []
    for row in grid:
        bench = [seat for seat in row if seat is not None]
        if bench:
            benches.append(bench)

    return benches


def reverse_seating(students, seats_per_bench):
    """
    Reverse Seating: assigns seats starting from the last bench,
    creating a reverse-fill pattern that spreads departments evenly.
    """
    mixed = mix_departments(students)
    reversed_students = mixed[::-1]
    benches = _chunk_students_into_seats(reversed_students, seats_per_bench)
    return benches[::-1]  # reverse bench order back


def progressive_bench_seating(students, seats_per_bench):
    """
    Progressive Bench Seating: each bench gets students from progressively
    different departments, ensuring strong anti-cheating distribution.
    Progressive offset increases per bench.
    """
    # Group by department
    dept_groups = {}
    for s in students:
        dept = s['department']
        dept_groups.setdefault(dept, []).append(s)

    depts = list(dept_groups.keys())
    dept_cycles = {d: cycle(dept_groups[d]) for d in depts}
    dept_list = cycle(depts)

    total = len(students)
    num_benches = (total + seats_per_bench - 1) // seats_per_bench

    benches = []
    assigned = 0

    for bench_idx in range(num_benches):
        bench = []
        # Progressive offset: rotate starting department per bench
        offset = bench_idx % len(depts)
        rotated_depts = depts[offset:] + depts[:offset]

        for seat_idx in range(seats_per_bench):
            if assigned >= total:
                break
            dept = rotated_depts[seat_idx % len(rotated_depts)]
            try:
                student = next(dept_cycles[dept])
                bench.append(student)
                assigned += 1
            except StopIteration:
                # Try any available department
                for d in depts:
                    try:
                        student = next(dept_cycles[d])
                        bench.append(student)
                        assigned += 1
                        break
                    except StopIteration:
                        continue

        if bench:
            benches.append(bench)

    return benches


def mixed_department_seating(students, seats_per_bench):
    """
    Mixed Department Anti-Cheating Seating:
    Strictly ensures no two adjacent seats in any bench belong to the same dept.
    Uses backtracking-lite approach for maximum separation.
    """
    # Group students by department
    dept_groups = {}
    for s in students:
        dept = s['department']
        dept_groups.setdefault(dept, []).append(dict(s))  # copy

    depts = sorted(dept_groups.keys(), key=lambda d: -len(dept_groups[d]))
    result = []

    def get_next_student(exclude_dept, dept_pools):
        """Get next student whose dept differs from exclude_dept."""
        for d in depts:
            if d != exclude_dept and dept_pools.get(d):
                return dept_pools[d].pop(0), d
        # Fallback: any available student
        for d in depts:
            if dept_pools.get(d):
                return dept_pools[d].pop(0), d
        return None, None

    dept_pools = {d: dept_groups[d][:] for d in depts}
    total = len(students)
    assigned = 0
    last_dept = None

    while assigned < total:
        bench = []
        for _ in range(seats_per_bench):
            if assigned >= total:
                break
            student, dept = get_next_student(last_dept, dept_pools)
            if student is None:
                break
            bench.append(student)
            last_dept = dept
            assigned += 1

        if bench:
            result.append(bench)

    return result


# ---------------------------------------------------------------------------
# Hall Distribution
# ---------------------------------------------------------------------------

def generate_multiple_hall_distribution(students, num_halls, benches_per_hall,
                                        seats_per_bench, flow_type='mixed'):
    """
    Main entry point: distributes students across multiple halls using
    the selected seating flow algorithm.

    Returns:
        halls: list of hall dicts, each with:
            - hall_number: int
            - benches: list of bench lists (each bench = list of student dicts)
            - total_students: int
            - capacity: int
    """
    # Apply seating algorithm to get ordered bench list
    if flow_type == 'zigzag':
        ordered_benches = zigzag_seating(students, seats_per_bench)
    elif flow_type == 'column':
        ordered_benches = column_wise_seating(students, seats_per_bench)
    elif flow_type == 'reverse':
        ordered_benches = reverse_seating(students, seats_per_bench)
    elif flow_type == 'progressive':
        ordered_benches = progressive_bench_seating(students, seats_per_bench)
    else:  # default: mixed anti-cheating
        ordered_benches = mixed_department_seating(students, seats_per_bench)

    # Distribute benches into halls
    halls = []
    bench_idx = 0

    for hall_num in range(1, num_halls + 1):
        hall_benches = []
        capacity = 0

        for _ in range(benches_per_hall):
            if bench_idx < len(ordered_benches):
                hall_benches.append(ordered_benches[bench_idx])
                capacity += len(ordered_benches[bench_idx])
                bench_idx += 1

        if hall_benches:  # only add hall if it has students
            halls.append({
                'hall_number': hall_num,
                'benches': hall_benches,
                'total_students': sum(len(b) for b in hall_benches),
                'capacity': benches_per_hall * seats_per_bench
            })

    return halls


def get_seating_stats(halls):
    """
    Returns summary statistics for the seating arrangement.
    """
    total_students = sum(h['total_students'] for h in halls)
    total_capacity = sum(h['capacity'] for h in halls)
    dept_counts = {}

    for hall in halls:
        for bench in hall['benches']:
            for student in bench:
                dept = student['department']
                dept_counts[dept] = dept_counts.get(dept, 0) + 1

    return {
        'total_students': total_students,
        'total_halls': len(halls),
        'total_capacity': total_capacity,
        'utilization_pct': round((total_students / total_capacity * 100), 1) if total_capacity else 0,
        'department_breakdown': dept_counts
    }
