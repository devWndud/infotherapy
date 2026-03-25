a, b, c = map(int, input().split())

(a + b) % c
((a % c) + (b % c)) % c
(a * b) % c
((a % c) * (b % c)) % c