#include <stdio.h>

int main() {
    int counter = 1;

    do {
        printf("Iteration: %d\n", counter);
        counter *= 2;
    } while (counter <= 32);

    return 0;
}
