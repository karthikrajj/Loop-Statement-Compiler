#include <stdio.h>
#include <string.h>
#include <ctype.h>

char symbol_table[20][32];
int symbol_count = 0;

void add_variable(const char name[]) {
    for (int i = 0; i < symbol_count; i++) {
        if (strcmp(symbol_table[i], name) == 0) return;
    }
    strcpy(symbol_table[symbol_count++], name);
}

int is_variable_declared(const char name[]) {
    for (int i = 0; i < symbol_count; i++) {
        if (strcmp(symbol_table[i], name) == 0) return 1;
    }
    return 0;
}

int validate_expression(const char expr[]) {
    int i = 0;
    int len = strlen(expr);
    int errors = 0;

    while (i < len) {
        if (isalpha(expr[i])) {
            char var[32] = "";
            int idx = 0;
            while (i < len && isalnum(expr[i])) {
                var[idx++] = expr[i++];
            }
            var[idx] = '\0';

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

    symbol_count = 0;

    while (i < len) {
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

        if (code[i] == ' ' || code[i] == '\t' || code[i] == '\n') {
            i++; continue;
        }

        if (isalpha(code[i])) {
            char word[32] = "";
            int idx = 0;
            while (i < len && isalnum(code[i])) {
                word[idx++] = code[i++];
            }
            word[idx] = '\0';

            if (strcmp(word, "int") == 0) {
                while (i < len && code[i] == ' ') i++;
                char var[32] = "";
                int v = 0;
                while (i < len && isalnum(code[i])) var[v++] = code[i++];
                var[v] = '\0';
                add_variable(var);
            }
            else if (strcmp(word, "for") == 0) {
                in_loop = 1;
                body_statement_found = 0;

                while (i < len && code[i] != '(') i++;
                if (code[i] == '(') i++;

                char init[32] = "", cond[32] = "", update[32] = "";
                int k = 0;

                while (i < len && code[i] != ';' && code[i] != ')') init[k++] = code[i++];
                init[k] = '\0';
                if (i < len && code[i] == ';') { i++; k = 0; }
                else { printf("[ERROR]: Missing ';' after initialization!\n"); errors++; }

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
                in_loop = 1;
                body_statement_found = 0;

                while (i < len && code[i] != '(') i++;
                if (code[i] == '(') i++;

                char cond[32] = "";
                int k = 0;
                while (i < len && code[i] != ')') cond[k++] = code[i++];
                cond[k] = '\0';

                if (i < len && code[i] == ')') { i++; }
                else { printf("[ERROR]: Missing closing ')' in while loop condition!\n"); errors++; }

                errors += validate_expression(cond);
            }
            else if (strcmp(word, "do") == 0) {
                in_loop = 1;
                body_statement_found = 0;
            }
            else {
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

    printf("\n==========================================\n");
    printf("               PARSE TREE                 \n");
    printf("==========================================\n");
    printf("PROGRAM\n");

    while (i < len) {
        if (code[i] == ' ' || code[i] == '\t' || code[i] == '\n' || code[i] == '{' || code[i] == '}') {
            i++; continue;
        }

        if (isalpha(code[i])) {
            char word[32] = "";
            int idx = 0;
            while (i < len && isalnum(code[i])) {
                word[idx++] = code[i++];
            }
            word[idx] = '\0';

            if (strcmp(word, "int") == 0) {
                while (i < len && code[i] == ' ') i++;
                char var[32] = "";
                int v = 0;
                while (i < len && isalnum(code[i])) var[v++] = code[i++];
                var[v] = '\0';

                add_variable(var);
                printf("|-- Declaration\n");
                printf("|   \\-- int %s\n", var);
            }
            else if (strcmp(word, "for") == 0) {
                while (i < len && code[i] != '(') i++; i++;

                char init[32] = "", cond[32] = "", update[32] = "";
                int k = 0;

                while (i < len && code[i] != ';') init[k++] = code[i++]; init[k] = '\0'; i++; k = 0;
                while (i < len && code[i] != ';') cond[k++] = code[i++]; cond[k] = '\0'; i++; k = 0;
                while (i < len && code[i] != ')') update[k++] = code[i++]; update[k] = '\0'; i++;

                printf("\\-- ForLoop\n");
                printf("    |-- Initialization: %s\n", init);
                printf("    |-- Condition: %s\n", cond);
                printf("    |-- Update: %s\n", update);
            }
            else if (strcmp(word, "while") == 0) {
                while (i < len && code[i] != '(') i++; i++;

                char cond[32] = "";
                int k = 0;
                while (i < len && code[i] != ')') cond[k++] = code[i++]; cond[k] = '\0'; i++;

                printf("\\-- WhileLoop\n");
                printf("    |-- Condition: %s\n", cond);
            }
            else if (strcmp(word, "do") == 0) {
                printf("\\-- DoWhileLoop\n");
            }
            else {
                char stmt[64] = "";
                strcpy(stmt, word);
                int k = strlen(word);

                while (i < len && code[i] != ';' && code[i] != '\n' && code[i] != '}') {
                    stmt[k++] = code[i++];
                }
                stmt[k] = '\0';

                printf("    \\-- Body\n");
                printf("        \\-- Statement: %s\n", stmt);
            }
            continue;
        }
        i++;
    }
    printf("------------------------------------------\n");
}

int main() {
    char input[1024] = "";
    char line[128];

    printf("==========================================\n");
    printf("       LOOP COMPILER            \n");
    printf("==========================================\n");
    printf("Enter code (type 'END' on a new line to process):\n\n");

    while (1) {
        if (fgets(line, sizeof(line), stdin) == NULL) break;
        line[strcspn(line, "\n")] = 0;

        if (strcmp(line, "END") == 0) break;

        strcat(input, line);
        strcat(input, "\n");
    }

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
