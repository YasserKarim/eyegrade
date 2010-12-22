import utils
import re

param_min_num_questions = 4

# Numbers of questions in which the number of tables is changed
param_table_limits = [8, 24, 55]

def create_answer_sheet(template_file, output_file, variables,
                        num_questions, num_answers, model, num_tables = 0):
    replacements = {}
    for var in variables:
        replacements[re.compile('{{' + var + '}}')] = variables[var]
    answer_table = create_answer_table(num_questions, num_answers,
                                       model, num_tables)
    id_box = create_id_box
    replacements[re.compile('{{answer-table}}')] = answer_table
    replacements[re.compile('{{tabla-respuestas}}')] = answer_table
    replacements[re.compile('{{model}}')] = model
    replacements[re.compile('{{modelo}}')] = model
    replacements[re.compile(r'{{id-box\(([0-9]+),(.*)\)}}')] = __id_box_replacer
    exam_text = utils.read_file(template_file)
    for exp in replacements:
        exam_text = exp.sub(replacements[exp], exam_text)
    if isinstance(output_file, file):
        output_file.write(exam_text)
    else:
        file_ = open(output_file, 'w')
        file_.write(exam_text)
        file_.close()

def create_answer_table(num_questions, num_answers, model, num_tables = 0):
    """Returns a string with the answer tables of the asnwer sheet.

       Tables are LaTeX-formatted. 'num_questions' specifies the
       number of questions of the exam. 'num_answers' specifies the
       number of answers per question. 'num_tables' (optional)
       specifies the number of tables. If not specified or set to a
       non-positive vale, a number of tables that best fits the number
       of questions is chosen.

    """
    if num_questions < param_min_num_questions:
        raise Exception('Too few questions')
    if num_answers < 2:
        raise Exception('Too few answers per question')
    if num_tables <= 0:
        num_tables = __choose_num_tables(num_questions)
    elif num_tables * 2 > num_questions:
        raise Exception('Too many tables for the given number of questions')
    compact = (num_tables > 2)
    bits = utils.encode_model(model, num_tables, num_answers)
    bits_rows = __create_infobits(bits, num_tables, num_answers)
    tables, question_numbers = __table_geometry(num_questions, num_answers,
                                                num_tables)
    rows = __table_top(num_tables, num_answers, compact)
    for i, row_geometry in enumerate(tables):
        rows.append(__horizontal_line(row_geometry, num_answers, compact))
        rows.append(__build_row(i, row_geometry, question_numbers,
                                num_answers, bits_rows, compact))
    rows.append('\\end{tabular}')
    rows.append('\\end{center}')
    return '\n'.join(rows)


def create_id_box(label, num_digits):
    """Creates the ID box given a label to show and number of digits.

    """
    parts = ['\\begin{center}', '\Large']
    parts.append('\\begin{tabular}{l|' + num_digits * 'p{3mm}|' + '}')
    parts.append('\\cline{2-%d}'%(1 + num_digits))
    parts.append('\\textbf{%s}: '%label + num_digits * '& ' + '\\\\')
    parts.append('\\cline{2-%d}'%(1 + num_digits))
    parts.append('\\end{tabular}')
    parts.append('\\end{center}')
    return '\n'.join(parts)

def __id_box_replacer(match):
    """Takes a re.match object and returns the id box.

       Two groups expected: (1) number of digits; (2) label to show.

    """
    return create_id_box(match.group(2), int(match.group(1)))

def __choose_num_tables(num_questions):
    """Returns a good number of tables for the given number of questions."""
    num_tables = 1
    for numq in param_table_limits:
        if numq >= num_questions:
            break
        else:
            num_tables += 1
    return num_tables

def __table_geometry(num_questions, num_answers, num_tables):
    """Returns the geometry of the answer tables.

       The result is a tuple (tables, question_numbers) where:
       - 'tables' is a bidimensional list such that table[row][column]
       represents the number of answers for the question in 'row' /
       'column'. If 0, the question does not exist. If -1, a first row
       of infobits should be placed there; if -2, a second row.
       - 'question_numbers' is a list with the number of question of
       the first row of each table. The first question is numbered as
       1.

    """
    rows_per_table = num_questions // num_tables
    tables = rows_per_table * [num_tables * [num_answers]]
    question_numbers = []
    for i in range(0, num_tables):
        question_numbers.append(1 + i * rows_per_table)
    diff = num_questions - num_tables * rows_per_table
    if diff > 0:
        last_row = diff * [num_answers] + (num_tables - diff) * [-1]
        tables.append(last_row)
        acc = 0
        for i in range(1, num_tables):
            if i <= diff:
                acc += 1
            question_numbers[i] += acc
    if diff == 0:
        diff = num_tables
    tables.append(diff * [-1] + (num_tables - diff) * [-2])
    tables.append(diff * [-2] + (num_tables - diff) * [-0])
    return tables, question_numbers

def __horizontal_line(row_geometry, num_answers, compact):
    parts = []
    num_empty_columns = 1 if not compact else 0
    first = 2
    for i, geometry in enumerate(row_geometry):
        if geometry > 0 or geometry == -1:
            parts.append('\\cline{%d-%d}'%(first, first + num_answers - 1))
        first += 1 + num_empty_columns + num_answers
    return ' '.join(parts)

def __table_top(num_tables, num_answers, compact):
    middle_sep_format = 'p{3mm}' if not compact else ''
    middle_sep_header = ' & & ' if not compact else ' & '
    l = middle_sep_format.join(num_tables
                               * ['|'.join(['r'] + num_answers * ['c'] + [''])])
    l = '\\\\begin{tabular}{' + l + '}'
    lines = ['\\\\begin{center}', '\\large', l]
    parts = []
    for i in range(0, num_tables):
        parts_internal = []
        parts_internal.append('\\multicolumn{1}{c}{}')
        for j in range(0, num_answers):
            parts_internal.append('\\multicolumn{1}{c}{%s}'%chr(65 + j))
        parts.append(' & '.join(parts_internal))
    lines.append(middle_sep_header.join(parts) + ' \\\\\\\\')
    return lines

def __build_row(num_row, row_geometry, question_numbers, num_answers,
                infobits_row, compact):
    parts = []
    num_empty_columns = 1 if not compact else 0
    skip_cells = 0
    for i, geometry in enumerate(row_geometry):
        if geometry > 0:
            parts.append(__build_question_cell(num_row + question_numbers[i],
                                               geometry))
        elif geometry == -1:
            parts.append(infobits_row[0][i])
        elif geometry == -2:
            parts.append(infobits_row[1][i])
        else:
            skip_cells += 1 + num_empty_columns + num_answers
    row = ' & & '.join(parts) if not compact else ' & '.join(parts)
    if skip_cells > 0:
        row += ' & \\multicolumn{%d}{c}{}'%skip_cells
    return row + ' \\\\\\\\'

def __build_question_cell(num_question, num_answers):
    parts = [str(num_question)]
    for i in range(0, num_answers):
        parts.append('\\light{%s}'%chr(65 + i))
    return ' & '.join(parts)

def __create_infobits(bits, num_tables, num_answers):
    column_active = '\\multicolumn{1}{c}{$\\\\blacksquare$}'
    column_inactive = '\\multicolumn{1}{c}{}'
    parts = [[], []]
    for i in range(0, num_tables):
        data = bits[i * num_answers: (i + 1) * num_answers]
        for j in (0, 1):
            val = (j == 1)
            components = [column_inactive]
            for bit in data:
                if val ^ bit:
                    components.append(column_active)
                else:
                    components.append(column_inactive)
            parts[j].append(' & '.join(components))
    return parts