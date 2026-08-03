#include "../include/time_sync_retry.h"

#include <assert.h>

int main() {
    assert(!isTimeSyncRetryDue(59'999, 0, 60'000));
    assert(isTimeSyncRetryDue(60'000, 0, 60'000));
    assert(isTimeSyncRetryDue(50, 0xFFFF'FFF0, 60));
    return 0;
}
