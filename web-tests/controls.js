// Exercise the visible advanced-tools route, without bypassing UI state.
export async function openTools(page) {
 if (!(await page.locator('#detailTools').getAttribute('open') !== null)) await page.locator('#detailTools summary').click();
}
export async function closeTools(page) {
 if (await page.locator('#detailTools').getAttribute('open') !== null) await page.keyboard.press('Escape');
}
export async function tool(page, id, action='click') {
 const el=page.locator('#'+id);
 if (!await el.isVisible()) await openTools(page);
 await el[action]();
 if(action!=='focus')await closeTools(page);
}
