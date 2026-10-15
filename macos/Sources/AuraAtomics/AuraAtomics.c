#include "include/AuraAtomics.h"

bool aura_atomic_is_hardware_lock_free(const AuraArbitrationState *state) {
    if (!state) return false;
    return atomic_is_lock_free(&state->injection_enabled) &&
           atomic_is_lock_free(&state->arbitration_epoch);
}

void aura_atomic_init(AuraArbitrationState *state, bool enabled, uint64_t initial_epoch) {
    if (!state) return;
    atomic_store_explicit(&state->injection_enabled, enabled, memory_order_relaxed);
    atomic_store_explicit(&state->arbitration_epoch, initial_epoch, memory_order_relaxed);
}

bool aura_atomic_try_disable(AuraArbitrationState *state, uint64_t *out_new_epoch) {
    if (!state) return false;
    bool expected = true;
    // Compare-exchange true -> false using acquire-release ordering
    if (atomic_compare_exchange_strong_explicit(&state->injection_enabled,
                                                &expected,
                                                false,
                                                memory_order_acq_rel,
                                                memory_order_relaxed)) {
        // First external event detected! Increment epoch monotonically.
        uint_fast64_t prev = atomic_fetch_add_explicit(&state->arbitration_epoch, 1, memory_order_acq_rel);
        if (out_new_epoch) {
            *out_new_epoch = (uint64_t)(prev + 1);
        }
        return true;
    }
    // Already disabled; do nothing
    return false;
}

bool aura_atomic_is_enabled(const AuraArbitrationState *state) {
    if (!state) return false;
    return atomic_load_explicit(&state->injection_enabled, memory_order_acquire);
}

uint64_t aura_atomic_get_epoch(const AuraArbitrationState *state) {
    if (!state) return 0;
    return (uint64_t)atomic_load_explicit(&state->arbitration_epoch, memory_order_acquire);
}

uint64_t aura_atomic_enable(AuraArbitrationState *state) {
    if (!state) return 0;
    // Increment epoch to issue fresh tokens
    uint_fast64_t prev = atomic_fetch_add_explicit(&state->arbitration_epoch, 1, memory_order_acq_rel);
    uint64_t new_epoch = (uint64_t)(prev + 1);
    atomic_store_explicit(&state->injection_enabled, true, memory_order_release);
    return new_epoch;
}
