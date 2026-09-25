#!/usr/bin/env node
'use strict';
/**
 * Deprecated thin-instance generator.
 * Harbor now uses FULL independent QVM copies per QN-XX.
 * Delegates to materialize-qnode-copies.js.
 */
console.log('[generate-qnodes] thin instances are obsolete — delegating to materialize-qnode-copies.js');
require('./materialize-qnode-copies.js');
