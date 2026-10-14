"""Exact Teensy 1.62 CDC2-only non-waiting transmit substitution."""
import hashlib

UPSTREAM_SHA256 = '575F5852165647E39F059548AE244A4B426A8BE31BFEF57CC4A9044FA8A37A3B'
WRITE_ANCHOR = b'int usb_serial2_write(const void *buffer, uint32_t size)\n'
FREE_ANCHOR = b'int usb_serial2_write_buffer_free(void)\n'
END_ANCHOR = b'void usb_serial2_flush_output(void)\n'

WRITE = b'''int usb_serial2_write(const void *buffer, uint32_t size)
{
    (void)transmit_previous_timeout; /* Retained upstream latch; no diagnostic wait. */
    if (!usb_configuration || size == 0) return 0;
    const uint8_t previous = tx_noautoflush;
    tx_noautoflush = 1;
    __asm__ volatile("" ::: "memory");
    transfer_t *xfer = tx_transfer + tx_head;
    uint32_t available = tx_available;
    if (!available) {
        const uint32_t status = usb_transfer_status(xfer);
        if (!(status & 0xE8)) available = TX_SIZE;
    }
    if (size > available) {
        __asm__ volatile("" ::: "memory");
        tx_noautoflush = previous;
        __asm__ volatile("" ::: "memory");
        if (tx_available && tx_available < TX_SIZE) timer_start_oneshot();
        return 0;
    }
    uint8_t *txbuf = txbuffer + (tx_head * TX_SIZE);
    memcpy(txbuf + (TX_SIZE - available), buffer, size);
    tx_available = available - size;
    if (tx_available == 0) {
        usb_prepare_transfer(xfer, txbuf, TX_SIZE, 0);
        arm_dcache_flush_delete(txbuf, TX_SIZE);
        usb_transmit(CDC2_TX_ENDPOINT, xfer);
        if (++tx_head >= TX_NUM) tx_head = 0;
        timer_stop();
    }
    __asm__ volatile("" ::: "memory");
    tx_noautoflush = previous;
    __asm__ volatile("" ::: "memory");
    /* Retry any expiry consumed while the unchanged callback was suppressed. */
    if (tx_available && tx_available < TX_SIZE) timer_start_oneshot();
    return size;
}

'''

FREE = b'''int usb_serial2_write_buffer_free(void)
{
    if (!usb_configuration) return 0;
    const uint8_t previous = tx_noautoflush;
    tx_noautoflush = 1;
    __asm__ volatile("" ::: "memory");
    uint32_t available = tx_available;
    if (!available) {
        const uint32_t status = usb_transfer_status(tx_transfer + tx_head);
        if (!(status & 0xE8)) available = TX_SIZE;
    }
    __asm__ volatile("" ::: "memory");
    tx_noautoflush = previous;
    __asm__ volatile("" ::: "memory");
    if (tx_available && tx_available < TX_SIZE) timer_start_oneshot();
    return available;
}

'''

def transform(source):
    for anchor in (WRITE_ANCHOR, FREE_ANCHOR, END_ANCHOR):
        if source.count(anchor) != 1:
            raise ValueError('Missing or ambiguous CDC2 function anchor')
    if hashlib.sha256(source).hexdigest().upper() != UPSTREAM_SHA256:
        raise ValueError('Unsupported CDC2 SDK SHA256; refusing substitution')
    start, middle, end = (source.index(anchor) for anchor in
                          (WRITE_ANCHOR, FREE_ANCHOR, END_ANCHOR))
    if not start < middle < end:
        raise ValueError('Unexpected CDC2 function order')
    return source[:start] + WRITE + FREE + source[end:]
