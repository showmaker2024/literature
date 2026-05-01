# OpenFSI 红细胞膜参数对照与宏观物理量推导

本文档整理 `OpenFSI/example/3D/RBC_suspension` 这套红细胞模型中最常关心的五个膜参数：

- `mu0`
- `k`
- `ka`
- `kv`
- `kd`

并给出它们对应的宏观物理意义、代码中的定义位置、从离散模型到连续体量的常用映射公式，以及当前这套算例参数对应的数值结果。文中尽量区分三类信息：

1. 代码和输入文件里直接定义的量
2. 文献中的连续体映射公式
3. 为了换算到真实红细胞物理单位而额外引入的标定假设

## 1. 当前模型的网格规模

单个红细胞网格见 [1rbc.data](/C:/OpenFSI/example/3D/RBC_suspension/1rbc.data:1)。其离散规模为：

- 顶点数：`3286`
- 边数：`9852`
- 三角面数：`6568`
- 二面角数：`9852`

因此，这是一张 `3286` 顶点的双凹红细胞膜三角网络。

## 2. 五个核心参数的中文对照表

| 参数 | 代码来源 | 直接物理含义 | 更接近的宏观量 | 调大后的典型效果 |
| --- | --- | --- | --- | --- |
| `mu0` | `Bond Coeffs #wlc` | 面内弹性网络的目标剪切模量尺度 | 膜面剪切模量 `\mu_s` | 红细胞更难被拉伸和剪切，面内变形减小 |
| `k` | `Dihedral Coeffs #bend` | 离散二面角弯曲刚度 | 连续体弯曲刚度 `\kappa` | 红细胞更难弯曲、翻卷和起皱 |
| `ka` | `Angle Coeffs #rbc` | 总面积约束强度 | 全局面积模量的一部分 | 总表面积更不容易偏离参考值 |
| `kv` | `Angle Coeffs #rbc` | 总体积约束强度 | 体积约束强度 | 红细胞总体积更不容易变化 |
| `kd` | `Angle Coeffs #rbc` | 局部三角面片面积约束强度 | 局部面内不可压缩性的一部分 | 局部面片更不容易塌陷或过度拉伸 |

对实际调参最有帮助的理解方式是：

- `mu0` 主要控制“膜面内硬不硬”
- `k` 主要控制“膜抗弯硬不硬”
- `ka` 和 `kd` 主要控制“面积能不能乱变”
- `kv` 主要控制“体积能不能乱变”

## 3. 这些参数在代码里的定义

### 3.1 `mu0` 的定义

`Bond Coeffs #wlc` 的参数顺序在 [bond_wlc.cpp](/C:/OpenFSI/src/structure_potential/bond_wlc.cpp:176) 中为：

```cpp
type, kT, rnorm0, rmax, mu0, m, gammaC, gammaT
```

其中平衡边长由 [bond_wlc.cpp](/C:/OpenFSI/src/structure_potential/bond_wlc.cpp:212) 给出：

```cpp
equilibrium_distance = rnorm0 * rmax
```

这里的 `mu0` 不是普通意义上“某一根弹簧的刚度常数”，而是该膜网络模型所目标对应的面剪切模量尺度。代码内部会根据 `mu0` 反推弹簧项中的系数，使整张三角网络在小变形极限下表现出目标剪切模量。

### 3.2 `ka`、`kv`、`kd` 的定义

`Angle Coeffs #rbc` 的参数顺序在 [angle_rbc.cpp](/C:/OpenFSI/src/structure_potential/angle_rbc.cpp:556) 中为：

```cpp
type, Cq, q, ka, Atot0, kv, Vtot0, kd, A0
```

它们在力表达式中的出现位置可见 [angle_rbc.cpp](/C:/OpenFSI/src/structure_potential/angle_rbc.cpp:455) 到 [angle_rbc.cpp](/C:/OpenFSI/src/structure_potential/angle_rbc.cpp:457)：

```cpp
alpha_a = -kd*(Ak-A0)/(4.0*Ak*A0);
beta_a  = -ka*(Atot-Atot0)/(4.0*Ak*Atot0);
beta_v  = -kv*(Vtot-Vtot0)/(6.0*Vtot0);
```

可直接看出：

- `kd` 控制局部三角面片面积偏离 `A0` 时的恢复作用
- `ka` 控制总面积偏离 `Atot0` 时的恢复作用
- `kv` 控制总体积偏离 `Vtot0` 时的恢复作用

### 3.3 `k` 的定义

`Dihedral Coeffs #bend` 的参数顺序在 [dihedral_bend.cpp](/C:/OpenFSI/src/structure_potential/dihedral_bend.cpp:387) 中为：

```cpp
type, k, phi0
```

弯曲能表达式可从 [dihedral_bend.cpp](/C:/OpenFSI/src/structure_potential/dihedral_bend.cpp:230) 附近读出：

```cpp
dphi = phi - phi0[type];
E_bend = k * (1 - cos(dphi))
```

因此：

- `k` 是离散二面角弯曲能系数
- `phi0` 是参考二面角，也可理解为无残余弯曲时偏好的局部几何角度

## 4. 从离散参数到宏观力学量的常用映射

这一节的公式不是仓库里直接写成“宏观输出”的，而是该类红细胞网络模型在文献中常用的连续体映射。这里采用的是 Fedosov 这一模型家族的标准关系。

### 4.1 面剪切模量 `\mu_s`

在这套模型里，`mu0` 就是目标的膜面剪切模量：

$$
\mu_s = \mu_0
$$

这条等式是在模型建模层面成立的。也就是说，`mu0` 本身就不是待换算的中间量，而是离散网络要实现的目标面剪切模量。

更细一点地说，对于 WLC-POW 膜网络，小变形线性极限下的剪切模量满足：

$$
\mu_0^{\mathrm{WLC-POW}}
=
\frac{\sqrt{3}\,k_B T}{4 p l_m x_0}
\left(
\frac{x_0}{2(1-x_0)^3}
-\frac{1}{4(1-x_0)^2}
+\frac{1}{4}
\right)
+
\frac{\sqrt{3}\,k_p (m+1)}{4 l_0^{m+1}}
$$

这里的关键点不是手算这条式子，而是理解：代码通过 `kT`、`rnorm0`、`rmax`、`m` 等参数共同构造单边弹性，并以 `mu0` 作为目标剪切模量尺度。

### 4.2 面积模量 `K`

对这一类红细胞三角网络，常用的二维面积模量（也可理解为表面体积模量或 area dilation modulus）近似写为：

$$
K = 2\mu_0 + k_a + k_d
$$

这个式子非常有用，因为它解释了为什么：

- 只调 `mu0` 会影响剪切与伸张
- 只调 `ka`、`kd` 会让面积变化更难发生
- 三者共同决定表面的“胀缩阻力”

### 4.3 表面杨氏模量 `Y_s`

二维各向同性膜的表面杨氏模量可由 `K` 和 `\mu_0` 给出：

$$
Y_s = \frac{4K\mu_0}{K+\mu_0}
$$

注意这里得到的是“表面杨氏模量”，不是三维实体材料那种以 `Pa` 为单位的体杨氏模量。它的量纲是 `N/m`，在当前算例里则首先是模型内部单位。

### 4.4 二维泊松比 `\nu`

同一模型下，二维泊松比为：

$$
\nu = \frac{K-\mu_0}{K+\mu_0}
$$

这也是一个很实用的检查量。若 `ka`、`kd` 很大，则 `K` 会远大于 `\mu_0`，膜会更接近面积不可压缩，`nu` 也会更接近 `1`。

### 4.5 连续体弯曲刚度 `\kappa`

二面角离散参数 `k` 与连续体 Helfrich 弯曲刚度 `\kappa` 的常用关系为：

$$
k = \frac{2}{\sqrt{3}}\kappa
$$

等价地，

$$
\kappa = \frac{\sqrt{3}}{2} k
$$

因此，代码里的 `k` 可以被看成连续体弯曲刚度的离散对应量，但两者并不相等，差一个固定的几何系数。

## 5. 当前这套算例参数的实际数值

下面以 [4rbc_poiseuille.data](/C:/OpenFSI/example/3D/RBC_suspension/4rbc_poiseuille.data:1) 为例。

### 5.1 输入文件中的原始参数

`Bond Coeffs #wlc` 中：

- `mu0 = 9.99999978E-03 \approx 0.01`

`Angle Coeffs #rbc` 中：

- `ka = 7.49999983E-03`
- `kv = 9.66000035E-02`
- `kd = 3.67000014E-01`
- `Atot0 = 2242.15283`
- `Vtot0 = 6430.45166`
- `A0 = 0.315937459`

`Dihedral Coeffs #bend` 中：

- `k = 1.32999998E-02 \approx 0.0133`

### 5.2 由公式得到的宏观量

由

$$
K = 2\mu_0 + k_a + k_d
$$

代入当前参数可得：

$$
K = 2\times 0.01 + 0.0075 + 0.3670 \approx 0.3945
$$

再代入表面杨氏模量公式：

$$
Y_s = \frac{4K\mu_0}{K+\mu_0}
$$

得到：

$$
Y_s \approx 0.0390
$$

再代入二维泊松比公式：

$$
\nu = \frac{K-\mu_0}{K+\mu_0}
$$

得到：

$$
\nu \approx 0.9506
$$

最后由

$$
\kappa = \frac{\sqrt{3}}{2}k
$$

得到连续体弯曲刚度：

$$
\kappa \approx 0.8660 \times 0.0133 \approx 0.0115
$$

因此，当前这套模型在内部单位下可概括为：

- 面剪切模量：`\mu_s = 0.01`
- 面积模量：`K \approx 0.3945`
- 表面杨氏模量：`Y_s \approx 0.0390`
- 二维泊松比：`\nu \approx 0.9506`
- 连续体弯曲刚度：`\kappa \approx 0.0115`

## 6. 如何把当前模型量标定到真实红细胞物理单位

这一节对应你之前提到的“完成 1”。由于当前仓库运行在 `units lj` 这类内部单位体系中，所以必须额外选取一套物理标定，才能把上面的无量纲或内部量换成真实红细胞单位。

### 6.1 标定思路

最常见的做法是：

1. 先用参考几何量把长度单位定下来
2. 再用文献中健康红细胞的典型剪切模量或弯曲刚度，把力学量映射到 SI 单位

### 6.2 用总面积和总体积确定长度尺度

当前模型给出的参考总面积和总体积分别是：

$$
A_{\mathrm{model}} = 2242.15283
$$

$$
V_{\mathrm{model}} = 6430.45166
$$

若采用健康红细胞常见的物理标定值：

$$
A_{\mathrm{phys}} \approx 135 \,\mu m^2
$$

$$
V_{\mathrm{phys}} \approx 94 \,\mu m^3
$$

则可分别得到长度尺度：

$$
\ell_A = \sqrt{\frac{A_{\mathrm{phys}}}{A_{\mathrm{model}}}}
$$

$$
\ell_V = \sqrt[3]{\frac{V_{\mathrm{phys}}}{V_{\mathrm{model}}}}
$$

代入数值：

$$
\ell_A = \sqrt{\frac{135}{2242.15283}} \approx 0.2454 \,\mu m
$$

$$
\ell_V = \sqrt[3]{\frac{94}{6430.45166}} \approx 0.2445 \,\mu m
$$

二者非常接近，这说明当前参考几何与常见健康红细胞的面积-体积比是自洽的。因此可取：

$$
1 \text{ 个模型长度单位} \approx 0.245 \,\mu m
$$

### 6.3 用剪切模量进行力学标定

健康红细胞膜常用的参考面剪切模量可取：

$$
\mu_s^{\mathrm{phys}} \approx 4.73 \,\mu N/m
$$

而当前模型内部：

$$
\mu_s^{\mathrm{model}} = 0.01
$$

因此若以剪切模量为主标定，则 1 个模型剪切模量单位对应：

$$
\frac{\mu_s^{\mathrm{phys}}}{\mu_s^{\mathrm{model}}}
=
\frac{4.73\,\mu N/m}{0.01}
=
473 \,\mu N/m
$$

于是可得：

- `mu0 = 0.01` 对应 `4.73 \,\mu N/m`
- `Y_s = 0.0390` 对应

$$
0.0390 \times 473 \approx 18.45 \,\mu N/m
$$

- `K = 0.3945` 对应

$$
0.3945 \times 473 \approx 186.6 \,\mu N/m
$$

这些数值在量纲上都是“表面模量”，单位是 `N/m`，这里写成 `\mu N/m` 更符合红细胞文献习惯。

### 6.4 用弯曲刚度进行交叉检查

健康红细胞膜的常用弯曲刚度可取：

$$
\kappa^{\mathrm{phys}} \approx 2.4\times 10^{-19} \,J
$$

而当前模型内部：

$$
\kappa^{\mathrm{model}} \approx 0.0115
$$

因此若用当前模型弯曲刚度去反推 1 个模型弯曲刚度单位，则有：

$$
1 \text{ 个模型弯曲刚度单位}
\approx
\frac{2.4\times10^{-19}}{0.0115}
\approx
2.08\times10^{-17}\,J
$$

这一步主要用于一致性检查。严格来说，完整的单位换算还需要时间尺度和力尺度的统一标定；但对于膜力学参数本身，这个数量级已经足够用来判断当前模型是否落在典型 RBC 范围附近。

## 7. 每个参数该怎么理解和调整

### 7.1 `mu0`

- 宏观意义：膜面剪切模量
- 作用方向：控制红细胞在流场中的面内拉伸、剪切与整体软硬
- 调大后：红细胞更硬，更不易被拉长
- 调小时：红细胞更软，更容易被流场拉变形

这是最值得优先调的参数。

### 7.2 `k`

- 宏观意义：弯曲刚度
- 作用方向：控制膜的抗弯曲能力
- 调大后：更不容易折叠、卷曲、起皱
- 调小时：更容易出现弯折和局部起伏

这是第二个最值得优先调的参数。

### 7.3 `ka`

- 宏观意义：全局面积守恒强度
- 作用方向：防止总表面积偏离参考值
- 调大后：总表面积变化更受限制
- 调小时：总面积更容易偏离参考值

### 7.4 `kv`

- 宏观意义：总体积守恒强度
- 作用方向：防止总体积偏离参考值
- 调大后：更接近不可压缩囊泡
- 调小时：体积更容易变化

### 7.5 `kd`

- 宏观意义：局部三角面片面积守恒强度
- 作用方向：抑制局部面片畸变
- 调大后：局部网格更稳，更不容易塌陷
- 调小时：局部面片更容易被拉扯变形

## 8. 审核时需要注意的几点

1. `mu0`、`k`、`ka`、`kv`、`kd` 都首先是模型内部单位下的参数，不是直接输入 SI 单位。
2. `mu0` 与宏观膜面剪切模量的对应关系最直接；`k` 与连续体弯曲刚度 `\kappa` 的对应关系则需要乘以 `\sqrt{3}/2`。
3. `Y_s` 和 `K` 都是二维膜的表面模量，不是三维实体的体模量。
4. 第 6 节中的真实物理单位换算依赖所选的红细胞参考面积、体积、剪切模量和弯曲刚度，因此它属于“带标定假设的推导”，不是代码自动给出的唯一答案。

## 9. 参考来源

### 9.1 仓库内代码

- [bond_wlc.cpp](/C:/OpenFSI/src/structure_potential/bond_wlc.cpp:176)
- [angle_rbc.cpp](/C:/OpenFSI/src/structure_potential/angle_rbc.cpp:455)
- [dihedral_bend.cpp](/C:/OpenFSI/src/structure_potential/dihedral_bend.cpp:230)
- [4rbc_poiseuille.data](/C:/OpenFSI/example/3D/RBC_suspension/4rbc_poiseuille.data:1)

### 9.2 连续体映射与物理标定文献

- D. A. Fedosov, *Multiscale Modeling of Blood Flow and Soft Matter*，博士论文，Brown University.
- 文中使用了该模型家族常见的 WLC-POW 膜参数映射、面积模量/杨氏模量/泊松比关系，以及离散二面角弯曲刚度到连续体弯曲刚度的关系。

