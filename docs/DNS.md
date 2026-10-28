# Blocking LG's ads with DNS, for the TV only

`webos-clean` changes settings on the TV. The ad tiles and banners LG serves still come from LG's servers, so
the other half is to block those names in your DNS. [hugobatista/lg-tv-ad-block](https://github.com/hugobatista/lg-tv-ad-block)
keeps a list in hosts format with two layers:

| Layer | URL | Notes |
|---|---|---|
| Normal | `https://raw.githubusercontent.com/hugobatista/lg-tv-ad-block/main/list` | Ads, tracking, recommendations. |
| Aggressive | `https://raw.githubusercontent.com/hugobatista/lg-tv-ad-block/main/list-store` | Also the LG Content Store: you can no longer install or update apps. Not recommended. |

**Apply it to the TV only.** Besides LG's own domains, the normal list also blocks names other devices need,
for example `developers.google.com`, `discovery.meethue.com` (Philips Hue), `mediaservices.cdn-apple.com` and some
Prime Video, Pluto TV and Tubi hosts. Added globally, it breaks things elsewhere in your home.

## Pi-hole v6: a group for the TV

In the web interface:

1. **Groups** → add a group `LG TV`.
2. **Clients** → add the TV's IP address (give it a fixed lease in your router first) and put it in the
   groups `Default` and `LG TV`.
3. **Lists** → add the normal list URL, then edit its groups: **only** `LG TV`, not `Default`.
4. **Tools → Update Gravity**.

Check from the TV (as root): `nslookup ads.lgtvcommon.com <pihole-ip>` should give no address, while
`nslookup www.youtube.com <pihole-ip>` still resolves. From any other device, `discovery.meethue.com` must
still resolve.

If an app on the TV stops working (Prime Video, Pluto, Tubi...), look in Pi-hole's query log for the TV's IP
and allow that domain for the `LG TV` group only.

## AdGuard Home

Add the list under **Filters → DNS blocklists**, then under **Settings → Client settings** add the TV and
give it its own filtering, or add the list as a custom rule restricted with `$client=<tv-ip>`.
