#pragma once

#include <stdint.h>

inline bool isTimeSyncRetryDue(
    uint32_t currentTime,
    uint32_t lastAttemptTime,
    uint32_t retryIntervalMs
) {
    return currentTime - lastAttemptTime >= retryIntervalMs;
}
