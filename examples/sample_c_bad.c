#include <stdio.h>

// Violates: arrays + loops
int main() {
    int arr[5] = {1,2,3,4,5}; // array violation
    for (int i = 0; i < 5; ++i) { // loop violation
        printf("%d ", arr[i]);
    }
    return 0;
}
