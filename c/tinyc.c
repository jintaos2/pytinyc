

int main() {
    int i;
    int a;
    i = 0;
    while (i < 10) {
        i = i + 1;
        if (i == 3 | i == 5) {
            continue;
        }
        if (i == 8) {
            break;
        }
        a = factor(i);
        print(a);
    }
    return 0;
}

int factor(int n) {
    if (n < 2) {
        return 1;
    }
    return n * factor(n - 1);
}

// int add(int a, int b){
//     int c;
//     c = 4;
//     return a + b + c;
// }