#include <stdio.h>
#include <string.h>
#include <ctype.h>

#define MAX_SYMBOLS 64
#define MAX_SYM_LEN 64

char symbol_table[MAX_SYMBOLS][MAX_SYM_LEN];
int symbol_count = 0;

void add_variable(const char name[]) {
    if (strlen(name) == 0) return;
    for (int i = 0; i < symbol_count; i++) {
        if (strcmp(symbol_table[i], name) == 0) return;
    }
    if (symbol_count < MAX_SYMBOLS) {
        strncpy(symbol_table[symbol_count++], name, MAX_SYM_LEN - 1);
    }
}

int is_variable_declared(const char name[]) {
    for (int i = 0; i < symbol_count; i++) {
        if (strcmp(symbol_table[i], name) == 0) return 1;
    }
    return 0;
}

int is_keyword_or_builtin(const char name[]) {
    static const char *keywords[] = {
        "int", "float", "char", "double", "void", "long", "short", "unsigned",
        "return", "if", "else", "for", "while", "do", "break", "continue",
        "switch", "case", "default", "sizeof", "static", "const", "struct",
        "main", "printf", "scanf", "include", "stdio", "h"
    };
    int count = sizeof(keywords) / sizeof(keywords[0]);
    for (int i = 0; i < count; i++) {
        if (strcmp(name, keywords[i]) == 0) return 1;
    }
    return 0;
}

/* Lexical Analysis: prints token stream for web interface and grading */
void print_tokens(const char code[]) {
    int i = 0;
    int len = strlen(code);
    int line = 1;
    int col = 1;

    printf("\n==========================================\n");
    printf("                 TOKENS                   \n");
    printf("==========================================\n");

    while (i < len) {
        char c = code[i];

        // Newline
        if (c == '\n') {
            line++;
            col = 1;
            i++;
            continue;
        }

        // Whitespace
        if (c == ' ' || c == '\t' || c == '\r') {
            col++;
            i++;
            continue;
        }

        // Preprocessor directive: #include ...
        if (c == '#') {
            int start_col = col;
            char prep[128] = "";
            int p = 0;
            while (i < len && code[i] != '\n' && p < 127) {
                prep[p++] = code[i++];
                col++;
            }
            prep[p] = '\0';
            printf("<PREPROCESSOR, \"%s\", %d, %d>\n", prep, line, start_col);
            continue;
        }

        // Single-line comment: // ...
        if (c == '/' && i + 1 < len && code[i + 1] == '/') {
            while (i < len && code[i] != '\n') {
                i++;
                col++;
            }
            continue;
        }

        // Multi-line comment: /* ... */
        if (c == '/' && i + 1 < len && code[i + 1] == '*') {
            i += 2;
            col += 2;
            while (i + 1 < len && !(code[i] == '*' && code[i + 1] == '/')) {
                if (code[i] == '\n') {
                    line++;
                    col = 1;
                } else {
                    col++;
                }
                i++;
            }
            if (i + 1 < len) {
                i += 2;
                col += 2;
            }
            continue;
        }

        // String literal: "..."
        if (c == '"') {
            int start_col = col;
            char str_lit[128] = "";
            int s = 0;
            i++;
            col++;
            while (i < len && code[i] != '"' && code[i] != '\n' && s < 125) {
                if (code[i] == '\\' && i + 1 < len) {
                    str_lit[s++] = code[i++];
                    col++;
                }
                str_lit[s++] = code[i++];
                col++;
            }
            if (i < len && code[i] == '"') {
                i++;
                col++;
            }
            str_lit[s] = '\0';
            printf("<STRING, \"%s\", %d, %d>\n", str_lit, line, start_col);
            continue;
        }

        // Identifier or Keyword
        if (isalpha((unsigned char)c) || c == '_') {
            int start_col = col;
            char word[64] = "";
            int w = 0;
            while (i < len && (isalnum((unsigned char)code[i]) || code[i] == '_') && w < 63) {
                word[w++] = code[i++];
                col++;
            }
            word[w] = '\0';

            const char *type = is_keyword_or_builtin(word) ? "KEYWORD" : "IDENTIFIER";
            printf("<%s, \"%s\", %d, %d>\n", type, word, line, start_col);
            continue;
        }

        // Number constant
        if (isdigit((unsigned char)c)) {
            int start_col = col;
            char num[64] = "";
            int n = 0;
            while (i < len && (isdigit((unsigned char)code[i]) || code[i] == '.') && n < 63) {
                num[n++] = code[i++];
                col++;
            }
            num[n] = '\0';
            printf("<NUMBER, \"%s\", %d, %d>\n", num, line, start_col);
            continue;
        }

        // Multi-character operators
        if (i + 1 < len) {
            char op2[3] = {code[i], code[i + 1], '\0'};
            if (strcmp(op2, "++") == 0 || strcmp(op2, "--") == 0 ||
                strcmp(op2, "+=") == 0 || strcmp(op2, "-=") == 0 ||
                strcmp(op2, "*=") == 0 || strcmp(op2, "/=") == 0 ||
                strcmp(op2, "==") == 0 || strcmp(op2, "!=") == 0 ||
                strcmp(op2, "<=") == 0 || strcmp(op2, ">=") == 0 ||
                strcmp(op2, "&&") == 0 || strcmp(op2, "||") == 0) {
                printf("<OPERATOR, \"%s\", %d, %d>\n", op2, line, col);
                i += 2;
                col += 2;
                continue;
            }
        }

        // Single-character operators
        if (strchr("+-*/%=<>!&|^~?", c) != NULL) {
            char op1[2] = {c, '\0'};
            printf("<OPERATOR, \"%s\", %d, %d>\n", op1, line, col);
            i++;
            col++;
            continue;
        }

        // Delimiters
        if (strchr(";,(){}[]:", c) != NULL) {
            char del[2] = {c, '\0'};
            printf("<DELIMITER, \"%s\", %d, %d>\n", del, line, col);
            i++;
            col++;
            continue;
        }

        // Other character
        i++;
        col++;
    }
    printf("------------------------------------------\n");
}

int validate_expression(const char expr[]) {
    int i = 0;
    int len = strlen(expr);
    int errors = 0;

    // Check empty condition
    int has_content = 0;
    for (int k = 0; k < len; k++) {
        if (!isspace((unsigned char)expr[k])) {
            has_content = 1;
            break;
        }
    }
    if (!has_content) {
        printf("[ERROR]: Missing condition expression in loop header!\n");
        return 1;
    }

    // Check trailing incomplete operator (e.g., "i < " or "i + ")
    int last_non_space = len - 1;
    while (last_non_space >= 0 && isspace((unsigned char)expr[last_non_space])) {
        last_non_space--;
    }
    if (last_non_space >= 0) {
        char last_char = expr[last_non_space];
        // If ends with ++ or --, that's valid postfix!
        int is_inc_dec = (last_non_space >= 1 &&
                          ((last_char == '+' && expr[last_non_space - 1] == '+') ||
                           (last_char == '-' && expr[last_non_space - 1] == '-')));
        
        if (!is_inc_dec && (last_char == '<' || last_char == '>' || last_char == '=' ||
            last_char == '!' || last_char == '+' || last_char == '-' ||
            last_char == '*' || last_char == '/' || last_char == '&' ||
            last_char == '|' || last_char == '%')) {
            printf("[ERROR]: Invalid expression! Missing operand after '%c'.\n", last_char);
            errors++;
        }
    }

    // Semantic check: identifiers must be declared variables (unless keyword/builtin)
    while (i < len) {
        // Skip string literals in statements like printf("%d\n", i)
        if (expr[i] == '"') {
            i++;
            while (i < len && expr[i] != '"') {
                if (expr[i] == '\\' && i + 1 < len) i++;
                i++;
            }
            if (i < len && expr[i] == '"') i++;
            continue;
        }

        if (isalpha((unsigned char)expr[i]) || expr[i] == '_') {
            char var[32] = "";
            int idx = 0;
            while (i < len && (isalnum((unsigned char)expr[i]) || expr[i] == '_') && idx < 31) {
                var[idx++] = expr[i++];
            }
            var[idx] = '\0';

            if (is_keyword_or_builtin(var)) {
                continue;
            }

            if (!is_variable_declared(var)) {
                printf("[ERROR]: Undeclared variable '%s' used!\n", var);
                errors++;
            }
        } else {
            i++;
        }
    }
    return errors;
}

int validate_inc_dec_expression(const char update_expr[]) {
    int errors = 0;
    int len = strlen(update_expr);

    if (len == 0) {
        printf("[ERROR]: Missing increment/decrement expression in for loop header!\n");
        return 1;
    }

    if (strstr(update_expr, "+-") != NULL || strstr(update_expr, "-+") != NULL) {
        printf("[ERROR]: Invalid operator combination in update expression '%s'!\n", update_expr);
        errors++;
        return errors;
    }

    int has_operator = 0;
    for (int i = 0; i < len; i++) {
        if (update_expr[i] == '+' || update_expr[i] == '-' || update_expr[i] == '=') {
            has_operator = 1;
            break;
        }
    }

    if (!has_operator) {
        printf("[ERROR]: Invalid update expression '%s'! Missing increment or decrement operator.\n", update_expr);
        errors++;
    }

    errors += validate_expression(update_expr);

    return errors;
}

int validate_code(const char code[]) {
    int i = 0;
    int len = strlen(code);
    int errors = 0;
    int brace_balance = 0;
    int body_statement_found = 0;
    int in_loop = 0;
    int in_do_loop = 0;

    symbol_count = 0;

    while (i < len) {
        // Skip preprocessor directives (#include ...)
        if (code[i] == '#') {
            while (i < len && code[i] != '\n') i++;
            continue;
        }

        // Skip comments (// and /* */)
        if (code[i] == '/' && i + 1 < len && code[i + 1] == '/') {
            while (i < len && code[i] != '\n') i++;
            continue;
        }
        if (code[i] == '/' && i + 1 < len && code[i + 1] == '*') {
            i += 2;
            while (i + 1 < len && !(code[i] == '*' && code[i + 1] == '/')) i++;
            if (i + 1 < len) i += 2;
            continue;
        }

        // Skip string literals
        if (code[i] == '"') {
            i++;
            while (i < len && code[i] != '"' && code[i] != '\n') {
                if (code[i] == '\\' && i + 1 < len) i++;
                i++;
            }
            if (i < len && code[i] == '"') i++;
            continue;
        }

        if (code[i] == '{') {
            brace_balance++;
            i++; continue;
        }
        if (code[i] == '}') {
            brace_balance--;
            if (brace_balance < 0) {
                printf("[ERROR]: Unmatched closing brace '}' found!\n");
                errors++;
            }
            i++; continue;
        }

        if (code[i] == ' ' || code[i] == '\t' || code[i] == '\n' || code[i] == '\r') {
            i++; continue;
        }

        if (isalpha((unsigned char)code[i]) || code[i] == '_') {
            char word[32] = "";
            int idx = 0;
            while (i < len && (isalnum((unsigned char)code[i]) || code[i] == '_') && idx < 31) {
                word[idx++] = code[i++];
            }
            word[idx] = '\0';

            // Variable Declaration
            if (strcmp(word, "int") == 0 || strcmp(word, "float") == 0 || strcmp(word, "char") == 0 || strcmp(word, "double") == 0) {
                while (i < len && code[i] == ' ') i++;
                char var[32] = "";
                int v = 0;
                while (i < len && (isalnum((unsigned char)code[i]) || code[i] == '_') && v < 31) {
                    var[v++] = code[i++];
                }
                var[v] = '\0';
                add_variable(var);

                // Check for function declaration like main()
                while (i < len && code[i] == ' ') i++;
                if (i < len && code[i] == '(') {
                    // Function header, skip parameter list
                    while (i < len && code[i] != ')') i++;
                    if (i < len && code[i] == ')') i++;
                    continue;
                }

                // Check for semicolon after variable declaration
                int has_semicolon = 0;
                while (i < len && code[i] != '\n' && code[i] != '}') {
                    if (code[i] == ';') {
                        has_semicolon = 1;
                        i++;
                        break;
                    }
                    i++;
                }
                if (!has_semicolon) {
                    printf("[ERROR]: Missing ';' after variable declaration '%s'!\n", var);
                    errors++;
                }
            }
            else if (strcmp(word, "for") == 0) {
                in_loop = 1;
                body_statement_found = 0;

                while (i < len && code[i] != '(') i++;
                if (code[i] == '(') i++;

                char init[64] = "", cond[64] = "", update[64] = "";
                int k = 0;

                while (i < len && code[i] != ';' && code[i] != ')') init[k++] = code[i++];
                init[k] = '\0';
                if (i < len && code[i] == ';') { i++; k = 0; }
                else { printf("[ERROR]: Missing ';' after initialization!\n"); errors++; }

                // Check if init declares a variable: "int i = 0"
                const char *p_init = init;
                while (*p_init && isspace((unsigned char)*p_init)) p_init++;
                if (strncmp(p_init, "int ", 4) == 0) {
                    p_init += 4;
                    while (*p_init && isspace((unsigned char)*p_init)) p_init++;
                    char lvar[32] = "";
                    int lv = 0;
                    while (*p_init && (isalnum((unsigned char)*p_init) || *p_init == '_') && lv < 31) {
                        lvar[lv++] = *p_init++;
                    }
                    lvar[lv] = '\0';
                    add_variable(lvar);
                }

                while (i < len && code[i] != ';' && code[i] != ')') cond[k++] = code[i++];
                cond[k] = '\0';
                if (i < len && code[i] == ';') { i++; k = 0; }
                else { printf("[ERROR]: Missing ';' after condition!\n"); errors++; }

                while (i < len && code[i] != ')') update[k++] = code[i++];
                update[k] = '\0';
                if (i < len && code[i] == ')') { i++; }
                else { printf("[ERROR]: Missing closing ')' in for loop header!\n"); errors++; }

                errors += validate_expression(init);
                errors += validate_expression(cond);
                errors += validate_inc_dec_expression(update);
            }
            else if (strcmp(word, "while") == 0) {
                if (in_do_loop) {
                    // Trailing while of do-while loop
                    in_do_loop = 0;
                    while (i < len && code[i] != '(') i++;
                    if (code[i] == '(') i++;

                    char cond[64] = "";
                    int k = 0;
                    while (i < len && code[i] != ')') cond[k++] = code[i++];
                    cond[k] = '\0';

                    if (i < len && code[i] == ')') { i++; }
                    else { printf("[ERROR]: Missing closing ')' in do-while loop condition!\n"); errors++; }

                    errors += validate_expression(cond);

                    // Must have semicolon
                    while (i < len && (code[i] == ' ' || code[i] == '\t')) i++;
                    if (i < len && code[i] == ';') {
                        i++;
                    } else {
                        printf("[ERROR]: Missing ';' after do-while loop condition!\n");
                        errors++;
                    }
                } else {
                    // Standard while loop
                    in_loop = 1;
                    body_statement_found = 0;

                    while (i < len && code[i] != '(') i++;
                    if (code[i] == '(') i++;

                    char cond[64] = "";
                    int k = 0;
                    while (i < len && code[i] != ')') cond[k++] = code[i++];
                    cond[k] = '\0';

                    if (i < len && code[i] == ')') { i++; }
                    else { printf("[ERROR]: Missing closing ')' in while loop condition!\n"); errors++; }

                    errors += validate_expression(cond);
                }
            }
            else if (strcmp(word, "do") == 0) {
                in_loop = 1;
                in_do_loop = 1;
                body_statement_found = 0;
            }
            else {
                // Statement within or outside loop
                char stmt[64] = "";
                strcpy(stmt, word);
                int k = strlen(word);

                while (i < len && code[i] != ';' && code[i] != '\n' && code[i] != '}') {
                    stmt[k++] = code[i++];
                }
                stmt[k] = '\0';

                errors += validate_expression(stmt);
                if (in_loop) {
                    body_statement_found = 1;
                }
            }
            continue;
        }
        i++;
    }

    if (brace_balance > 0) {
        printf("[ERROR]: Missing closing brace '}'! (%d unclosed)\n", brace_balance);
        errors++;
    }

    if (in_loop && !body_statement_found) {
        printf("[ERROR]: No statement found after loop condition header!\n");
        errors++;
    }

    return errors;
}

void print_parse_tree(const char code[]) {
    int i = 0;
    int len = strlen(code);
    symbol_count = 0;
    int depth = 0;
    int in_do = 0;

    printf("\n==========================================\n");
    printf("               PARSE TREE                 \n");
    printf("==========================================\n");
    printf("PROGRAM\n");

    while (i < len) {
        // Skip comments and preprocessors
        if (code[i] == '#') {
            while (i < len && code[i] != '\n') i++;
            continue;
        }
        if (code[i] == '/' && i + 1 < len && code[i + 1] == '/') {
            while (i < len && code[i] != '\n') i++;
            continue;
        }
        if (code[i] == '/' && i + 1 < len && code[i + 1] == '*') {
            i += 2;
            while (i + 1 < len && !(code[i] == '*' && code[i + 1] == '/')) i++;
            if (i + 1 < len) i += 2;
            continue;
        }

        if (code[i] == '{') {
            depth++;
            i++;
            continue;
        }
        if (code[i] == '}') {
            if (depth > 0) depth--;
            i++;
            continue;
        }

        if (code[i] == ' ' || code[i] == '\t' || code[i] == '\n' || code[i] == '\r') {
            i++; continue;
        }

        if (isalpha((unsigned char)code[i]) || code[i] == '_') {
            char word[32] = "";
            int idx = 0;
            while (i < len && (isalnum((unsigned char)code[i]) || code[i] == '_') && idx < 31) {
                word[idx++] = code[i++];
            }
            word[idx] = '\0';

            char pad[32] = "";
            for (int p = 0; p < depth && p < 6; p++) {
                strcat(pad, "    ");
            }

            if (strcmp(word, "int") == 0 || strcmp(word, "float") == 0 || strcmp(word, "char") == 0) {
                while (i < len && code[i] == ' ') i++;
                char var[32] = "";
                int v = 0;
                while (i < len && (isalnum((unsigned char)code[i]) || code[i] == '_') && v < 31) {
                    var[v++] = code[i++];
                }
                var[v] = '\0';

                // Skip function main()
                while (i < len && code[i] == ' ') i++;
                if (i < len && code[i] == '(') {
                    while (i < len && code[i] != ')') i++;
                    if (i < len && code[i] == ')') i++;
                    printf("|-- Function: %s\n", var);
                    continue;
                }

                add_variable(var);
                printf("%s|-- Declaration\n", pad);
                printf("%s|   \\-- %s %s\n", pad, word, var);

                while (i < len && code[i] != ';' && code[i] != '\n') i++;
                if (i < len && code[i] == ';') i++;
            }
            else if (strcmp(word, "for") == 0) {
                while (i < len && code[i] != '(') i++; i++;

                char init[64] = "", cond[64] = "", update[64] = "";
                int k = 0;

                while (i < len && code[i] != ';') init[k++] = code[i++]; init[k] = '\0'; if (i < len) i++; k = 0;
                while (i < len && code[i] != ';') cond[k++] = code[i++]; cond[k] = '\0'; if (i < len) i++; k = 0;
                while (i < len && code[i] != ')') update[k++] = code[i++]; update[k] = '\0'; if (i < len) i++;

                // If init declares a variable, add it
                const char *p_init = init;
                while (*p_init && isspace((unsigned char)*p_init)) p_init++;
                if (strncmp(p_init, "int ", 4) == 0) {
                    p_init += 4;
                    while (*p_init && isspace((unsigned char)*p_init)) p_init++;
                    char lvar[32] = "";
                    int lv = 0;
                    while (*p_init && (isalnum((unsigned char)*p_init) || *p_init == '_') && lv < 31) {
                        lvar[lv++] = *p_init++;
                    }
                    lvar[lv] = '\0';
                    add_variable(lvar);
                }

                printf("%s\\-- ForLoop\n", pad);
                printf("%s    |-- Initialization: %s\n", pad, init);
                printf("%s    |-- Condition: %s\n", pad, cond);
                printf("%s    |-- Update: %s\n", pad, update);
            }
            else if (strcmp(word, "while") == 0) {
                while (i < len && code[i] != '(') i++; i++;

                char cond[64] = "";
                int k = 0;
                while (i < len && code[i] != ')') cond[k++] = code[i++]; cond[k] = '\0'; if (i < len) i++;

                if (in_do) {
                    in_do = 0;
                    printf("%s    |-- Condition: %s\n", pad, cond);
                    while (i < len && code[i] != ';') i++;
                    if (i < len && code[i] == ';') i++;
                } else {
                    printf("%s\\-- WhileLoop\n", pad);
                    printf("%s    |-- Condition: %s\n", pad, cond);
                }
            }
            else if (strcmp(word, "do") == 0) {
                in_do = 1;
                printf("%s\\-- Do-WhileLoop\n", pad);
            }
            else {
                char stmt[64] = "";
                strcpy(stmt, word);
                int k = strlen(word);

                while (i < len && code[i] != ';' && code[i] != '\n' && code[i] != '}') {
                    stmt[k++] = code[i++];
                }
                stmt[k] = '\0';

                printf("%s    \\-- Body\n", pad);
                printf("%s        \\-- Statement: %s\n", pad, stmt);
                if (i < len && code[i] == ';') i++;
            }
            continue;
        }
        i++;
    }
    printf("------------------------------------------\n");
}

int main() {
    char input[16384] = "";
    char line[512];

    printf("==========================================\n");
    printf("       LOOP COMPILER            \n");
    printf("==========================================\n");
    printf("Enter code (type 'END' on a new line to process):\n\n");

    while (1) {
        if (fgets(line, sizeof(line), stdin) == NULL) break;
        line[strcspn(line, "\r\n")] = 0;

        if (strcmp(line, "END") == 0) break;

        if (strlen(input) + strlen(line) + 2 < sizeof(input)) {
            strcat(input, line);
            strcat(input, "\n");
        }
    }

    // Phase 1: Lexical Analysis
    print_tokens(input);

    // Phase 2: Syntax and Semantic Validation
    printf("\n--- COMPILATION LOG ---\n");
    int total_errors = validate_code(input);

    if (total_errors == 0) {
        printf("[SUCCESS] Code is Syntactically & Semantically Valid!\n");
        print_parse_tree(input);
    } else {
        printf("\n[FAILURE] Compilation failed with %d error(s). Parse tree suppressed.\n", total_errors);
    }

    return 0;
}
