// main.c - 測試 clang-tidy 禁用陣列檢查
#include <stdio.h>

int main() {
    // 這行會被 misc-forbid-arrays 抓到
    int numbers[5] = {1, 2, 3, 4, 5};
    
    printf("Array test\n");
    return 0;
}
