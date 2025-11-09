// main.cpp - 測試 clang-tidy 禁用迴圈與函式檢查
#include <iostream>
#include <algorithm>
#include <vector>

int main() {
    std::vector<int> data = {5, 2, 8, 1, 9};
    
    // 這行會被 misc-forbid-functions 抓到（如果 sort 在禁用清單）
    std::sort(data.begin(), data.end());
    
    // 這行會被 misc-forbid-loops 抓到
    for (int i = 0; i < data.size(); i++) {
        std::cout << data[i] << " ";
    }
    std::cout << std::endl;
    
    return 0;
}
