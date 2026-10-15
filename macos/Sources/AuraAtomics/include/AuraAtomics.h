#ifndef AuraAtomics_h
#define AuraAtomics_h

#include <stdbool.h>
#include <stdint.h>
#include <stdatomic.h>

#ifdef __cplusplus
extern "C" {
#endif

/// State shared between the minimal CGEventTap callback and the output coordinator.
typedef struct {
    _Atomic(bool) injection_enabled;
    _Atomic(uint_fast64_t) arbitration_epoch;
} AuraArbitrationState;

/// Verifies that atomic operations on this platform are truly lock-free in hardware.
bool aura_atomic_is_hardware_lock_free(const AuraArbitrationState *state);

/// Initializes the arbitration state with initial values.
void aura_atomic_init(AuraArbitrationState *state, bool enabled, uint64_t initial_epoch);

/// Attempts to atomically flip injection_enabled from true -> false.
/// If successful (the first external event), increments arbitration_epoch
/// and writes the newly incremented epoch into `out_new_epoch`.
/// Memory order: memory_order_acq_rel.
bool aura_atomic_try_disable(AuraArbitrationState *state, uint64_t *out_new_epoch);

/// Checks whether injection is currently enabled.
/// Memory order: memory_order_acquire.
bool aura_atomic_is_enabled(const AuraArbitrationState *state);

/// Retrieves the current arbitration epoch.
/// Memory order: memory_order_acquire.
uint64_t aura_atomic_get_epoch(const AuraArbitrationState *state);

/// Re-enables injection by incrementing the epoch and setting injection_enabled = true.
/// Memory order: memory_order_release.
/// Returns the newly issued epoch.
uint64_t aura_atomic_enable(AuraArbitrationState *state);

#ifdef __cplusplus
}
#endif

#endif /* AuraAtomics_h */
