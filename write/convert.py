import json
import random
import string

import pypandoc


class LineBuffer:
    def __init__(self, text):
        self.lines = text.strip().split("\n")
        self.i = 0

    def pop(self) -> str:
        if self.i == len(self.lines):
            raise SyntaxError("File terminated unexpectedly")
        self.i += 1
        return self.lines[self.i - 1]

    def empty(self):
        return self.i == len(self.lines)


def directive_type(line):
    if not any(line.startswith(f"# {x} ") for x in ["BEGIN", "END", "INPUT", "CONFIG", "DEFINE"]):
        return None, None, None
    tokens = line.split(" ", 3)
    return tokens[1], tokens[2] if len(tokens) > 2 else "", tokens[3] if len(tokens) > 3 else ""


def get_points(line):
    tokens = line.split(" ")
    point_sec = tokens[-1]
    if not point_sec or point_sec[0] != "[" or point_sec[-1] != "]":
        return line, None
    try:
        return " ".join(tokens[:-1]), float(point_sec[1:-1])
    except ValueError:
        return line, None


def rand_id():
    return ''.join(random.choices(string.ascii_uppercase, k=32))


def parse(text):
    return {
        "html": pypandoc.convert_text(text, "html5", "md", ["--mathjax"]),
        "tex": pypandoc.convert_text(text, "latex", "md"),
        "text": text,
    }


def parse_input_lines(lines):
    if not lines:
        raise SyntaxError("No INPUT directives found in QUESTION")
    _, directive, rest = directive_type(lines[0])
    if directive == "OPTION" or directive == "SELECT":
        options = []
        for line in lines:
            _, other_directive, rest = directive_type(line)
            if other_directive != directive:
                raise SyntaxError("Multiple INPUT types found in a single QUESTION")
            options.append(parse(rest))
        return "multiple_choice" if directive == "OPTION" else "select_all", options
    elif directive in ("SHORT_ANSWER", "SHORT_CODE_ANSWER", "LONG_ANSWER", "LONG_CODE_ANSWER"):
        if len(lines) > 1:
            raise SyntaxError("Multiple INPUT directives found for a {}".format(directive))
        if directive == "SHORT_ANSWER":
            return "short_answer", None
        elif directive == "SHORT_CODE_ANSWER":
            return "short_code_answer", None
        try:
            num_lines = int(rest or "10")
        except TypeError:
            raise SyntaxError("Expected integer as option for {}".format(directive))
        if directive == "LONG_ANSWER":
            return "long_answer", num_lines
        elif directive == "LONG_CODE_ANSWER":
            return "long_code_answer", num_lines
    raise SyntaxError("Unrecognized directive: {}".format(directive))


def consume_rest_of_question(buff):
    contents = []
    input_lines = []
    substitutions = {}
    while True:
        line = buff.pop()
        mode, directive, rest = directive_type(line)
        if mode is None:
            if input_lines and line.strip():
                raise SyntaxError("Unexpected content in QUESTION after INPUT")
            elif not input_lines:
                contents.append(line)
        elif mode == "INPUT":
            input_lines.append(line)
        elif mode == "END":
            if directive == "QUESTION":
                question_type, options = parse_input_lines(input_lines)
                return {
                    "id": rand_id(),
                    "type": question_type,
                    **parse("\n".join(contents)),
                    "options": options,
                    "substitutions": substitutions,
                }
            else:
                raise SyntaxError("Unexpected END in QUESTION")
        elif mode == "DEFINE":
            substitutions[directive] = rest.split(" ")
        else:
            raise SyntaxError("Unexpected directive in QUESTION")


def consume_rest_of_group(buff, end):
    group_contents = []
    questions = []
    started_question = False
    substitutions = {}
    while True:
        line = buff.pop()
        mode, directive, rest = directive_type(line)
        if mode is None:
            if started_question and line.strip():
                raise SyntaxError("Unexpected text in GROUP after QUESTIONs started")
            elif not started_question:
                group_contents.append(line)
        elif mode == "BEGIN" and directive == "QUESTION":
            started_question = True
            title, points = get_points(rest)
            if title:
                raise SyntaxError("Unexpected arguments passed in BEGIN QUESTION directive")
            question = consume_rest_of_question(buff)
            question["points"] = points
            questions.append(question)
        elif mode == "END" and directive == end:
            return "\n".join(group_contents), questions, substitutions
        elif mode == "DEFINE":
            substitutions[directive] = rest.split(" ")
        else:
            raise SyntaxError("Unexpected directive in GROUP")


def convert(text):
    buff = LineBuffer(text)
    groups = []
    public = None
    config = []
    substitutions = {}

    try:
        while not buff.empty():
            line = buff.pop()
            if not line.strip():
                continue
            mode, directive, rest = directive_type(line)
            if mode == "CONFIG":
                if directive in ["SCRAMBLE_GROUPS", "SCRAMBLE_QUESTIONS", "SCRAMBLE_OPTIONS"]:
                    config.append(directive.lower())
                else:
                    raise SyntaxError("Unexpected CONFIG directive {}".format(directive))
            elif mode == "BEGIN" and directive in ["GROUP", "PUBLIC"]:
                title, points = get_points(rest)
                body, questions, group_substitutions = consume_rest_of_group(buff, directive)
                group = {
                    "name": title,
                    "points": points,
                    **parse(body),
                    "questions": questions,
                    "substitutions": group_substitutions,
                }
                if directive == "PUBLIC":
                    if public:
                        raise SyntaxError("Only one PUBLIC block is allowed")
                    public = group
                else:
                    groups.append(group)
            elif mode == "DEFINE":
                substitutions[directive] = rest.split(" ")
            else:
                raise SyntaxError("Unexpected directive")
    except SyntaxError as e:
        raise SyntaxError("Parse stopped on line {} with error {}".format(buff.i, e))

    return {
        "public": public,
        "groups": groups,
        "config": config,
        "substitutions": substitutions,
    }


def convert_str(text):
    return json.dumps(convert(text))