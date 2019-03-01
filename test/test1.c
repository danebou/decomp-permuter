#ifdef ACTUAL
int test_general() {
    return 64;
}
#else
int test_general() {
    return PERM_GENERAL(32,64);
}
#endif

#ifdef ACTUAL
int test_general_multi() {
    return 64;
}
#else
int test_general_multi() {
    return PERM_GENERAL(32,48,64);
}
#endif