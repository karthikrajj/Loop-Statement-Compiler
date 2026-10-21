#include <stdio.h>

int main() {
    int rows = 3;
    int cols = 3;

    for (int i = 0; i < rows; i++) {
        int j = 0;
        while (j < cols) {
            printf("[%d, %d] ", i, j);
            j++;
        }
        printf("\n");
    }

    return 0;
}
