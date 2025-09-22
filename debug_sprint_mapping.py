#!/usr/bin/env python3

from developer_graph.sprint_mapping import _SECTION_RE, _START_RE, _END_RE

# Read the sprint status file
with open('docs/sprints/planning/SPRINT_STATUS.md', 'r', encoding='utf-8') as f:
    text = f.read()

# Test the section regex
matches = list(_SECTION_RE.finditer(text))
print(f'Total matches: {len(matches)}')

for i, match in enumerate(matches[:5]):
    number = match.group(1)
    name = match.group(2)
    body = match.group('body')
    
    print(f'\nMatch {i}:')
    print(f'  Number: {number}')
    print(f'  Name: {name}')
    print(f'  Body start: {body[:100]}...')
    
    # Test start date regex
    start_match = _START_RE.search(body)
    print(f'  Start match: {start_match.groups() if start_match else None}')
    
    # Test end date regex
    end_match = _END_RE.search(body)
    print(f'  End match: {end_match.groups() if end_match else None}')
